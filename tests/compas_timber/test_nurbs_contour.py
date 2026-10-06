import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL
from compas.tolerance import Tolerance
from compas_brep.curves import NurbsCurve

from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import Contour
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import NurbsContour
from compas_timber.fabrication import knotvector_from_btlx
from compas_timber.fabrication import knotvector_to_btlx
from compas_timber.fabrication import nurbs_curve_from_btlx
from compas_timber.fabrication.btlx import contour_to_xml
from compas_timber.fabrication.btlx import nurbs_contour_to_tessellated_xml
from compas_timber.fabrication.btlx import nurbs_contour_to_xml
from compas_timber.fabrication.btlx import split_nurbs_curve
from compas_timber.model import TimberModel

# control points of a closed, wavy contour which fits on a 300 x 200 plate
WAVE_POINTS = [
    Point(20, 20, 0),
    Point(100, 90, 0),
    Point(200, -30, 0),
    Point(280, 40, 0),
    Point(280, 160, 0),
    Point(180, 120, 0),
    Point(80, 190, 0),
    Point(20, 150, 0),
    Point(20, 20, 0),
]


@pytest.fixture
def plate():
    outline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(300, 200, 0), Point(300, 0, 0), Point(0, 0, 0)])
    return Plate.from_outline_thickness(outline, 20.0)


@pytest.fixture
def closed_curve():
    return NurbsCurve.from_points(WAVE_POINTS, degree=3)


@pytest.fixture
def open_curve():
    return NurbsCurve.from_points(WAVE_POINTS[:-1], degree=3)


########################################################################
# knot vector conversion
########################################################################


def test_knotvector_to_btlx_drops_first_and_last():
    assert knotvector_to_btlx([0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0]) == [0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0]


def test_knotvector_from_btlx_repeats_first_and_last():
    assert knotvector_from_btlx([0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0]) == [0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0]


def test_knotvector_matches_btlx_spec_example():
    """The worked example on p.106 of the BTLx 2.3.0 spec: Count=10, Degree=3, 12 knots."""
    count, degree = 10, 3
    spec_knots = [0.0, 0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 4.0]

    assert len(spec_knots) == count + degree - 1

    full = knotvector_from_btlx(spec_knots)

    # a valid clamped cubic knot vector: length count + degree + 1, end multiplicity degree + 1
    assert len(full) == count + degree + 1
    assert full[: degree + 1] == [0.0] * (degree + 1)
    assert full[-(degree + 1) :] == [4.0] * (degree + 1)
    assert knotvector_to_btlx(full) == spec_knots


def test_knotvector_to_btlx_rejects_short_vector():
    with pytest.raises(ValueError):
        knotvector_to_btlx([0.0, 1.0])


def test_knotvector_from_btlx_rejects_empty():
    with pytest.raises(ValueError):
        knotvector_from_btlx([])


def test_nurbs_curve_from_btlx_roundtrip(closed_curve):
    btlx_knots = knotvector_to_btlx(closed_curve.knotvector)

    restored = nurbs_curve_from_btlx(closed_curve.points, closed_curve.weights, btlx_knots, closed_curve.degree)

    assert restored.degree == closed_curve.degree
    assert TOL.is_allclose(restored.knotvector, closed_curve.knotvector)
    assert TOL.is_allclose(restored.weights, closed_curve.weights)
    assert TOL.is_allclose(restored.points, closed_curve.points)


########################################################################
# NurbsContour
########################################################################


def test_nurbs_contour_start_point_and_closed(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0)

    assert TOL.is_allclose(contour.start_point, WAVE_POINTS[0])
    assert contour.is_closed


def test_nurbs_contour_open_curve_is_not_closed(open_curve):
    contour = NurbsContour([open_curve], depth=20.0)

    assert not contour.is_closed


def test_nurbs_contour_mixed_segments_close_the_loop(open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])

    contour = NurbsContour([open_curve, closing_line], depth=20.0)

    assert contour.is_closed
    assert [type(segment).__name__ for segment in contour.segments] == ["NurbsCurve", "Line"]


def test_nurbs_contour_rejects_empty_segments():
    with pytest.raises(ValueError, match="at least one segment"):
        NurbsContour([], depth=20.0)


def test_nurbs_contour_rejects_unsupported_segment_type(closed_curve):
    with pytest.raises(ValueError, match="NurbsCurve or Line"):
        NurbsContour([closed_curve, Polyline(WAVE_POINTS)], depth=20.0)


def test_nurbs_contour_rejects_disconnected_segments(open_curve):
    disconnected = Line(Point(500, 500, 0), Point(600, 600, 0))

    with pytest.raises(ValueError, match="must be connected"):
        NurbsContour([open_curve, disconnected], depth=20.0)


def test_nurbs_contour_rejects_unclamped_curve():
    # a uniform (unclamped) knot vector: the curve does not reach its first/last control point
    points = [Point(0, 0, 0), Point(10, 20, 0), Point(30, -10, 0), Point(50, 10, 0), Point(70, 0, 0)]
    knots = [float(i) for i in range(9)]
    curve = NurbsCurve.from_parameters(points, [1.0] * 5, knots, [1] * 9, 3)

    with pytest.raises(ValueError, match="clamped"):
        NurbsContour([curve], depth=20.0)


def test_nurbs_contour_to_polyline_tessellates(open_curve):
    contour = NurbsContour([open_curve], depth=20.0, tessellation_count=32)

    polyline = contour.to_polyline()

    assert isinstance(polyline, Polyline)
    assert len(polyline.points) == 33
    assert TOL.is_allclose(polyline[0], contour.start_point)


def test_nurbs_contour_closed_curve_to_polyline(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0, tessellation_count=32)

    polyline = contour.to_polyline()

    # the closed curve is split in two, so the polyline is made of two tessellated halves
    assert len(polyline.points) == 65
    assert polyline.is_closed


def test_nurbs_contour_to_polyline_joins_segments_without_duplicates(open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])
    contour = NurbsContour([open_curve, closing_line], depth=20.0, tessellation_count=16)

    polyline = contour.to_polyline()

    # 17 points for the curve, plus one for the end of the line (its start is shared)
    assert len(polyline.points) == 18
    assert polyline.is_closed


@pytest.mark.requires_occ
def test_nurbs_contour_to_brep_is_a_solid(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0, tessellation_count=32)

    brep = contour.to_brep()

    assert brep.is_solid
    assert brep.volume > 0.0


def test_nurbs_contour_scaled(open_curve):
    contour = NurbsContour([open_curve], depth=20.0)

    scaled = contour.scaled(2.0)

    assert scaled.depth == contour.depth * 2.0
    assert TOL.is_allclose(scaled.segments[0].points, [Point(*point) * 2.0 for point in open_curve.points])
    # knots are parametric, scaling the contour must not touch them
    assert TOL.is_allclose(scaled.segments[0].knotvector, open_curve.knotvector)
    assert scaled.segments[0].degree == open_curve.degree


def test_nurbs_contour_serialization_roundtrip(open_curve):
    contour = NurbsContour([open_curve], depth=20.0, tessellation_count=32)

    copy = json_loads(json_dumps(contour))

    assert copy.depth == contour.depth
    assert copy.depth_bounded == contour.depth_bounded
    assert copy.inclination == contour.inclination
    assert copy.tessellation_count == contour.tessellation_count
    assert TOL.is_allclose(copy.segments[0].points, open_curve.points)
    assert TOL.is_allclose(copy.segments[0].knotvector, open_curve.knotvector)


########################################################################
# XML serialization
########################################################################


def test_nurbs_contour_to_xml_structure(open_curve):
    contour = NurbsContour([open_curve], depth=20.0)

    root = nurbs_contour_to_xml(contour)

    assert root.tag == "Contour"
    assert root.attrib["Depth"] == "20.000"
    assert root.attrib["DepthBounded"] == "yes"
    assert root.attrib["Inclination"] == "0.000"
    assert [child.tag for child in root] == ["StartPoint", "NURBS"]

    start_point = root.find("StartPoint")
    assert start_point.attrib == {"X": "20.000", "Y": "20.000", "Z": "0.000"}


def test_nurbs_contour_to_xml_nurbs_element(open_curve):
    contour = NurbsContour([open_curve], depth=20.0)

    nurbs = nurbs_contour_to_xml(contour).find("NURBS")

    assert nurbs.attrib["Degree"] == str(open_curve.degree)
    assert nurbs.attrib["Count"] == str(len(open_curve.points))

    control_points = nurbs.findall("ControlPoints/ControlPoint")
    assert len(control_points) == len(open_curve.points)
    assert control_points[0].attrib["X"] == "20.000"
    assert control_points[0].attrib["Y"] == "20.000"
    assert control_points[0].attrib["Z"] == "0.000"
    assert float(control_points[0].attrib["W"]) == 1.0

    knots = [float(value) for value in nurbs.find("Knots").text.split()]
    assert len(knots) == len(open_curve.points) + open_curve.degree - 1
    assert TOL.is_allclose(knots, knotvector_to_btlx(open_curve.knotvector))


def test_nurbs_contour_to_xml_mixed_segments(open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])
    contour = NurbsContour([open_curve, closing_line], depth=20.0)

    root = nurbs_contour_to_xml(contour)

    assert [child.tag for child in root] == ["StartPoint", "NURBS", "Line"]
    end_point = root.find("Line/EndPoint")
    assert end_point.attrib == {"X": "20.000", "Y": "20.000", "Z": "0.000"}


def test_nurbs_contour_to_xml_per_segment_inclination(open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])
    contour = NurbsContour([open_curve, closing_line], depth=20.0, inclination=[10.0, -5.0])

    root = nurbs_contour_to_xml(contour)

    assert "Inclination" not in root.attrib
    assert root.find("NURBS").attrib["Inclination"] == "10.000"
    assert root.find("Line").attrib["Inclination"] == "-5.000"


def test_nurbs_contour_to_xml_rejects_mismatched_inclination(open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])
    contour = NurbsContour([open_curve, closing_line], depth=20.0, inclination=[10.0, -5.0, 1.0])

    with pytest.raises(ValueError, match="one inclination value or one per segment"):
        nurbs_contour_to_xml(contour)


def test_nurbs_knots_keep_full_precision():
    """Knots are parametric, rounding them to POINT_PRECISION would distort the curve."""
    # 9 control points of degree 3 give interior knots of 1/6, 2/6, ... which need more than 3 decimals
    curve = NurbsCurve.from_points(WAVE_POINTS[:-1] + [Point(60, 60, 0)], degree=3)
    contour = NurbsContour([curve], depth=20.0)
    expected = knotvector_to_btlx(curve.knotvector)

    knots = [float(value) for value in nurbs_contour_to_xml(contour).find("NURBS/Knots").text.split()]

    assert TOL.is_allclose(knots, expected, atol=1e-9)
    # at least one knot is not representable at POINT_PRECISION, which is what pins the higher precision
    assert any(abs(knot - round(knot, 3)) > 1e-9 for knot in expected)


def test_nurbs_weights_keep_full_precision():
    """A circle's weights are 0.7071..., rounding them to POINT_PRECISION would distort it."""
    from compas.geometry import Circle

    contour = NurbsContour([NurbsCurve.from_circle(Circle(50.0))], depth=20.0)

    root = nurbs_contour_to_xml(contour)
    weights = [float(cp.attrib["W"]) for cp in root.iter("ControlPoint")]

    assert any(abs(weight - round(weight, 3)) > 1e-9 for weight in weights)
    # the written weights still describe a circle
    for segment, nurbs in zip(contour.segments, root.iter("NURBS")):
        written = [float(cp.attrib["W"]) for cp in nurbs.iter("ControlPoint")]
        assert TOL.is_allclose(written, segment.weights, atol=1e-9)


########################################################################
# FreeContour integration
########################################################################


def test_free_contour_from_nurbs_curve(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    assert isinstance(contour, FreeContour)
    assert isinstance(contour.contour_param_object, NurbsContour)
    assert contour.ref_side_index == 0
    assert contour.counter_sink is True
    assert contour.params.header_attributes["Name"] == "FreeContour"
    assert contour.params.header_attributes["CounterSink"] == "yes"


def test_free_contour_from_nurbs_curve_default_depth(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate)

    # the plate is 20mm thick, and the contour lies on its top face
    assert TOL.is_close(contour.contour_param_object.depth, 20.0)


def test_free_contour_from_nurbs_curve_explicit_depth(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, depth=5.0, interior=True)

    assert TOL.is_close(contour.contour_param_object.depth, 5.0)


def test_free_contour_from_nurbs_curve_accepts_single_curve_or_list(plate, closed_curve):
    from_single = FreeContour.from_nurbs_curves_and_element(closed_curve, plate)
    from_list = FreeContour.from_nurbs_curves_and_element([closed_curve], plate)

    assert len(from_single.contour_param_object.segments) == len(from_list.contour_param_object.segments)
    assert TOL.is_allclose(from_single.contour_param_object.to_polyline(), from_list.contour_param_object.to_polyline())


def test_free_contour_from_nurbs_curve_transforms_to_ref_side(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    # the contour is stored in the local frame of the reference side, so it must no longer sit
    # on the world-space control points
    stored = contour.contour_param_object.segments[0].points
    assert not TOL.is_allclose(stored[0], WAVE_POINTS[0])
    # ...but it stays flat on the reference side
    assert all(TOL.is_zero(point.z) for point in stored)


def test_free_contour_from_nurbs_curve_open_requires_tool_position(plate, open_curve):
    with pytest.raises(ValueError, match="closed or a tool position"):
        FreeContour.from_nurbs_curves_and_element(open_curve, plate)


def test_free_contour_from_nurbs_curve_off_element_raises(plate, closed_curve):
    off_element = closed_curve.translated([0, 0, 137.0])

    with pytest.raises(ValueError, match="does not lay on one of the reference sides"):
        FreeContour.from_nurbs_curves_and_element(off_element, plate)


def test_get_ref_face_index(plate):
    polyline = Polyline([Point(20, 20, 0), Point(100, 90, 0), Point(200, 30, 0)])

    assert FreeContour.get_ref_face_index(polyline, plate) == 0


@pytest.mark.requires_occ
def test_free_contour_nurbs_applies_to_plate_geometry(plate, closed_curve):
    volume_before = plate.geometry.volume
    plate.add_features([FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)])

    geometry = plate.geometry

    assert geometry.is_solid
    assert geometry.volume < volume_before


@pytest.mark.requires_occ
def test_free_contour_nurbs_applies_to_beam_geometry():
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(600, 0, 0)), width=120, height=200)
    points = [Point(100, 20, 0), Point(200, 90, 0), Point(300, -30, 0), Point(400, 60, 0), Point(500, 20, 0), Point(300, 100, 0), Point(100, 20, 0)]
    curve = NurbsCurve.from_points(points, degree=3)
    ref_side_curve = curve.transformed(beam.ref_sides[0].to_transformation())

    contour = FreeContour.from_nurbs_curves_and_element(ref_side_curve, beam, depth=30.0, interior=True)
    beam.add_features([contour])

    assert isinstance(contour.contour_param_object, NurbsContour)
    assert beam.geometry.is_solid


def test_free_contour_nurbs_scaled(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, depth=5.0, interior=True)

    scaled = contour.scaled(2.0)

    assert TOL.is_close(scaled.contour_param_object.depth, 10.0)


def test_free_contour_nurbs_data_roundtrip(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, depth=5.0, interior=True)

    copy = json_loads(json_dumps(contour))

    assert isinstance(copy.contour_param_object, NurbsContour)
    assert copy.ref_side_index == contour.ref_side_index
    assert copy.tool_position == contour.tool_position
    assert TOL.is_close(copy.contour_param_object.depth, 5.0)
    assert TOL.is_allclose(copy.contour_param_object.segments[0].points, contour.contour_param_object.segments[0].points)


def test_free_contour_nurbs_serializes_as_contour_element(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    # NurbsContour occupies the same "Contour" slot as Contour does
    assert isinstance(contour.params.as_dict()["Contour"], NurbsContour)
    assert "DualContour" not in contour.params.as_dict()

    processing_element = BTLxWriter()._create_processing(contour)

    assert processing_element.tag == "FreeContour"
    assert [child.tag for child in processing_element] == ["Contour"]
    assert processing_element.find("Contour/NURBS") is not None


########################################################################
# splitting closed curves
########################################################################


@pytest.mark.parametrize("degree", [2, 3, 5])
def test_split_nurbs_curve_is_exact(degree):
    """The two halves together must describe exactly the same geometry as the original."""
    curve = NurbsCurve.from_points(WAVE_POINTS, degree=degree)
    start, end = curve.domain
    middle = 0.5 * (start + end)

    left, right = split_nurbs_curve(curve)

    for i in range(101):
        t = i / 100.0
        expected_left = curve.point_at(start + (middle - start) * t)
        actual_left = left.point_at(left.domain[0] + (left.domain[1] - left.domain[0]) * t)
        expected_right = curve.point_at(middle + (end - middle) * t)
        actual_right = right.point_at(right.domain[0] + (right.domain[1] - right.domain[0]) * t)
        assert expected_left.distance_to_point(actual_left) < 1e-9
        assert expected_right.distance_to_point(actual_right) < 1e-9


def test_split_nurbs_curve_halves_are_connected(closed_curve):
    left, right = split_nurbs_curve(closed_curve)

    assert TOL.is_allclose(left.points[-1], right.points[0])
    assert TOL.is_allclose(left.points[0], closed_curve.points[0])
    assert TOL.is_allclose(right.points[-1], closed_curve.points[-1])


def test_split_nurbs_curve_preserves_rational_weights():
    """A circle is rational, so its weights must survive the split."""
    from compas.geometry import Circle

    circle = NurbsCurve.from_circle(Circle(50.0))

    left, right = split_nurbs_curve(circle)

    for half in (left, right):
        for t in [i / 20.0 for i in range(21)]:
            point = half.point_at(half.domain[0] + (half.domain[1] - half.domain[0]) * t)
            assert TOL.is_close(point.distance_to_point(Point(0, 0, 0)), 50.0, atol=1e-9)


def test_split_nurbs_curve_rejects_parameter_outside_domain(open_curve):
    with pytest.raises(ValueError, match="not inside the curve"):
        split_nurbs_curve(open_curve, u=5.0)


def test_nurbs_contour_splits_closed_curve(closed_curve):
    """BTLx has no segment which starts where it ends, so a closed curve becomes two segments."""
    contour = NurbsContour([closed_curve], depth=20.0)

    assert len(contour.segments) == 2
    assert all(isinstance(segment, NurbsCurve) for segment in contour.segments)
    assert contour.is_closed


def test_nurbs_contour_does_not_split_open_curve(open_curve):
    contour = NurbsContour([open_curve], depth=20.0)

    assert len(contour.segments) == 1


def test_nurbs_contour_has_no_zero_length_segments(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0)

    for segment in contour.segments:
        start = NurbsContour._segment_start_point(segment)
        end = NurbsContour._segment_end_point(segment)
        assert start.distance_to_point(end) > 1e-6


def test_nurbs_contour_rejects_zero_length_line(open_curve):
    degenerate = Line(WAVE_POINTS[-2], WAVE_POINTS[-2])

    with pytest.raises(ValueError, match="length would be zero"):
        NurbsContour([open_curve, degenerate], depth=20.0)


def test_split_closed_curve_survives_btlx_roundtrip(tmp_path, plate, closed_curve):
    """The written file must contain two NURBS segments, neither of them degenerate."""
    plate.add_features([FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)])
    model = _mm_model()
    model.add_element(plate)

    read_model = _write_and_read(model, tmp_path)

    contours = [f.contour_param_object for e in read_model.elements() for f in e.features if isinstance(f.contour_param_object, NurbsContour)]
    restored = contours[0]

    assert len(restored.segments) == 2
    assert restored.is_closed
    for segment in restored.segments:
        start = NurbsContour._segment_start_point(segment)
        end = NurbsContour._segment_end_point(segment)
        assert start.distance_to_point(end) > 1e-6


########################################################################
# tessellated output for machines without NURBS support
########################################################################


def test_nurbs_contour_to_contour_has_no_nurbs(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0, tessellation_count=32)

    tessellated = contour.to_contour()

    assert isinstance(tessellated, Contour)
    assert not isinstance(tessellated, NurbsContour)
    assert tessellated.depth == contour.depth
    assert TOL.is_allclose(tessellated.polyline, contour.to_polyline())


def test_nurbs_contour_to_contour_serializes_as_lines_only(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0, tessellation_count=16)

    root = contour_to_xml(contour.to_contour())

    tags = [child.tag for child in root]
    assert "NURBS" not in tags
    assert set(tags) == {"StartPoint", "Line"}


@pytest.mark.requires_occ
def test_nurbs_contour_to_contour_keeps_geometry(closed_curve):
    contour = NurbsContour([closed_curve], depth=20.0, tessellation_count=64)

    # the tessellated contour is built from the very same polyline, so the solids agree
    assert TOL.is_close(contour.to_contour().to_brep().volume, contour.to_brep().volume, rtol=1e-9)


def test_writer_tessellates_nurbs_on_the_way_out(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    processing_element = BTLxWriter(tessellate=True)._create_processing(contour)

    assert processing_element.find("Contour/NURBS") is None
    assert processing_element.find("Contour/Line") is not None


def test_writer_leaves_the_model_alone_when_tessellating(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    BTLxWriter(tessellate=True)._create_processing(contour)

    assert isinstance(contour.contour_param_object, NurbsContour)


def test_writer_writes_nurbs_by_default(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    processing_element = BTLxWriter()._create_processing(contour)

    assert processing_element.find("Contour/NURBS") is not None


def test_tessellated_output_has_no_zero_length_segments(tmp_path, plate, closed_curve):
    """A dropped NURBS segment is what makes a closing line degenerate, so check none are left."""
    plate.add_features([FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)])
    model = _mm_model()
    model.add_element(plate)

    read_model = _write_and_read(model, tmp_path, tessellate=True)

    contours = [f.contour_param_object for e in read_model.elements() for f in e.features]
    assert contours
    assert not any(isinstance(c, NurbsContour) for c in contours)
    for contour in contours:
        assert contour.polyline.is_closed
        for a, b in zip(contour.polyline.points[:-1], contour.polyline.points[1:]):
            assert a.distance_to_point(b) > 1e-6


@pytest.mark.requires_occ
def test_tessellated_output_matches_the_nurbs_geometry(plate, closed_curve):
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True, tessellation_count=64)
    nurbs_contour = contour.contour_param_object

    assert TOL.is_close(nurbs_contour.to_contour().to_brep().volume, nurbs_contour.to_brep().volume, rtol=1e-9)


def test_tessellated_serializer_is_looked_up_by_registration(plate, closed_curve):
    """The writer picks the alternative from the registry, so it needs no knowledge of the type."""
    contour = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)

    assert BTLxWriter.TESSELLATED_SERIALIZERS["NurbsContour"] is nurbs_contour_to_tessellated_xml
    assert BTLxWriter.SERIALIZERS["NurbsContour"] is nurbs_contour_to_xml
    assert "Contour" not in BTLxWriter.TESSELLATED_SERIALIZERS
    assert contour_to_xml(contour.contour_param_object.to_contour()).tag == "Contour"


def test_a_type_without_a_tessellated_serializer_is_written_the_same_either_way(plate):
    polyline = Polyline([Point(20, 50, 0), Point(20, 150, 0), Point(80, 150, 0), Point(80, 50, 0), Point(20, 50, 0)])
    contour = FreeContour.from_polyline_and_element(polyline, plate, depth=5.0)

    plain = ET.tostring(BTLxWriter()._create_processing(contour))
    tessellated = ET.tostring(BTLxWriter(tessellate=True)._create_processing(contour))

    assert plain == tessellated


def test_the_same_model_writes_both_ways(tmp_path, plate, closed_curve):
    """The choice belongs to the export, so one model yields both files."""
    plate.add_features([FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)])
    model = _mm_model()
    model.add_element(plate)
    ns = "{https://www.design2machine.com}"

    nurbs_path = str(tmp_path / "nurbs.btlx")
    lines_path = str(tmp_path / "lines.btlx")
    BTLxWriter().write(model, nurbs_path)
    BTLxWriter(tessellate=True).write(model, lines_path)

    assert list(ET.parse(nurbs_path).getroot().iter(ns + "NURBS"))
    assert not list(ET.parse(lines_path).getroot().iter(ns + "NURBS"))


########################################################################
# BTLx round-trip
########################################################################


def _write_and_read(model, tmp_path, tessellate=False):
    path = str(tmp_path / "nurbs.btlx")
    BTLxWriter(tessellate=tessellate).write(model, path)
    reader = BTLxReader()
    read_model = reader.read(path)
    assert reader.errors == []
    return read_model


def _mm_model():
    return TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-6, relative=1e-6))


def test_btlx_roundtrip_preserves_nurbs_contour(tmp_path, plate, closed_curve):
    original = FreeContour.from_nurbs_curves_and_element(closed_curve, plate, interior=True)
    plate.add_features([original])
    model = _mm_model()
    model.add_element(plate)

    read_model = _write_and_read(model, tmp_path)

    contours = [feature.contour_param_object for element in read_model.elements() for feature in element.features if isinstance(feature.contour_param_object, NurbsContour)]
    assert len(contours) == 1

    restored = contours[0].segments[0]
    expected = original.contour_param_object.segments[0]
    assert restored.degree == expected.degree
    assert TOL.is_allclose(restored.knotvector, expected.knotvector)
    assert TOL.is_allclose(restored.weights, expected.weights)
    assert TOL.is_allclose(restored.points, expected.points, atol=1e-3)


def test_btlx_roundtrip_preserves_mixed_segments(tmp_path, plate, open_curve):
    closing_line = Line(WAVE_POINTS[-2], WAVE_POINTS[0])
    original = FreeContour.from_nurbs_curves_and_element([open_curve, closing_line], plate, interior=True)
    plate.add_features([original])
    model = _mm_model()
    model.add_element(plate)

    read_model = _write_and_read(model, tmp_path)

    contours = [feature.contour_param_object for element in read_model.elements() for feature in element.features if isinstance(feature.contour_param_object, NurbsContour)]
    restored = contours[0]

    assert [type(segment).__name__ for segment in restored.segments] == ["NurbsCurve", "Line"]
    expected_line = original.contour_param_object.segments[1]
    assert TOL.is_allclose(restored.segments[1].start, expected_line.start, atol=1e-3)
    assert TOL.is_allclose(restored.segments[1].end, expected_line.end, atol=1e-3)


def test_reader_still_returns_plain_contour_without_nurbs(tmp_path, plate):
    """A Contour made only of Line segments must keep deserializing to Contour, not NurbsContour."""
    model = _mm_model()
    model.add_element(plate)

    read_model = _write_and_read(model, tmp_path)

    contours = [feature.contour_param_object for element in read_model.elements() for feature in element.features]
    assert contours
    assert not any(isinstance(contour, NurbsContour) for contour in contours)


def test_reader_rejects_nurbs_with_wrong_count():
    from compas_timber.btlx.reader import _xml_to_nurbs_curve

    xml = """
    <NURBS Degree="3" Count="9">
      <ControlPoints>
        <ControlPoint X="0" Y="0" Z="0" W="1"/>
        <ControlPoint X="1" Y="1" Z="0" W="1"/>
        <ControlPoint X="2" Y="0" Z="0" W="1"/>
        <ControlPoint X="3" Y="1" Z="0" W="1"/>
      </ControlPoints>
      <Knots>0 0 0 0.5 1 1 1</Knots>
    </NURBS>
    """

    with pytest.raises(ValueError, match="Count=9 but has 4 control points"):
        _xml_to_nurbs_curve(ET.fromstring(xml))


def test_reader_parses_spec_style_nurbs_element():
    from compas_timber.btlx.reader import _xml_to_nurbs_curve

    xml = """
    <NURBS Degree="3" Count="4">
      <ControlPoints>
        <ControlPoint X="0" Y="0" Z="0" W="1"/>
        <ControlPoint X="10" Y="20" Z="0" W="0.5"/>
        <ControlPoint X="20" Y="0" Z="0" W="1"/>
        <ControlPoint X="30" Y="20" Z="0" W="1"/>
      </ControlPoints>
      <Knots>0 0 0 1 1 1</Knots>
    </NURBS>
    """

    curve = _xml_to_nurbs_curve(ET.fromstring(xml))

    assert curve.degree == 3
    assert len(curve.points) == 4
    assert curve.weights == [1.0, 0.5, 1.0, 1.0]
    assert curve.knotvector == [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
