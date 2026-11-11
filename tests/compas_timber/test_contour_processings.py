import math
import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.tolerance import TOL
from compas.tolerance import Tolerance
from compas_brep import Brep
from compas_brep import NurbsSurface

from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import Contour
from compas_timber.fabrication import DualContour
from compas_timber.fabrication.areas import Apertures
from compas_timber.fabrication.areas import GlueArea
from compas_timber.fabrication.areas import InsulationArea
from compas_timber.fabrication.areas import LockoutArea
from compas_timber.fabrication.areas import PlaningArea
from compas_timber.fabrication.areas import PlasterArea
from compas_timber.fabrication.contours import CrampAngleRefType
from compas_timber.fabrication.contours import CrampContour
from compas_timber.fabrication.contours import MillContour
from compas_timber.fabrication.contours import NailContour
from compas_timber.fabrication.contours import PenContour
from compas_timber.fabrication.contours import SawContour
from compas_timber.fabrication.contours import ScrewContour
from compas_timber.fabrication.contours import SimpleContour
from compas_timber.fabrication.contours import simple_contour_to_xml
from compas_timber.fabrication.free_surface import FreeSurface
from compas_timber.fabrication.free_surface import NurbsPatch
from compas_timber.model import TimberModel

BEAM_VOLUME = 1000.0 * 100.0 * 200.0
GUID = "{12345678-1234-1234-1234-123456789abc}"

# in the coordinates of a reference side: counter clockwise seen from outside of the element
SQUARE = [[100.0, 10.0, 0.0], [200.0, 10.0, 0.0], [200.0, 50.0, 0.0], [100.0, 50.0, 0.0], [100.0, 10.0, 0.0]]
HOLE = [[120.0, 20.0, 0.0], [140.0, 20.0, 0.0], [140.0, 40.0, 0.0], [120.0, 40.0, 0.0], [120.0, 20.0, 0.0]]
PATH = [[10.0, 10.0, 0.0], [110.0, 10.0, 0.0], [110.0, 50.0, 0.0]]


def _closed():
    return SimpleContour(Polyline(SQUARE))


def _material_processings():
    return [
        SawContour(Contour(Polyline(SQUARE), 50.0), tool_position="left"),
        MillContour(Contour(Polyline(SQUARE), 50.0), tool_position="left", counter_sink=True),
        PlaningArea(contour=_closed(), apertures=Apertures([SimpleContour(Polyline(HOLE))]), depth=2.0, tool_id=3),
        FreeSurface(surface=_flat_patch(-5.0), tool_id=4),
    ]


def _other_processings():
    return [
        NailContour(contour=SimpleContour(Polyline(PATH), nail_length=60.0, nail_spacing=100.0), tool_id=1),
        CrampContour(contour=SimpleContour(Polyline(PATH), nail_length=50.0, cramp_width=11.0, nail_spacing=[None, 80.0, 90.0], cramp_angle=30.0, cramp_angle_ref="grain")),
        ScrewContour(contour=SimpleContour(Polyline(PATH), screw_length=80.0, screw_diameter=6.0, nail_spacing=150.0)),
        PenContour(contour=SimpleContour(Polyline(PATH)), ref_side_index=2),
        GlueArea(contour=_closed(), apertures=Apertures([SimpleContour(Polyline(HOLE))]), glue_type="PU", glue_amount=120.0, tool_id=2),
        PlasterArea(contour=_closed(), thickness=15.0),
        InsulationArea(contour=_closed(), part_ref_guid=GUID),
        LockoutArea(contour=_closed(), for_sawing=False),
    ]


def _flat_patch(z, x=(0.0, 1000.0), y=(0.0, 100.0)):
    points = [[x[0], y[0], z], [x[1], y[0], z], [x[0], y[1], z], [x[1], y[1], z]]
    return NurbsPatch(points, [1.0] * 4, [0.0, 1.0], [0.0, 1.0], 1, 1, 2, 2)


def _volume(processing, beam=None):
    beam = beam or Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    return geometry.volume


def _volume_in_box(processing, corner_a, corner_b):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    box = Brep.from_box(Box.from_points([corner_a, corner_b]))
    return sum(piece.volume for piece in Brep.from_boolean_intersection(geometry, box))


def _write(model_unit, *processings):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features(list(processings))
    model = TimberModel(tolerance=Tolerance(unit=model_unit, absolute=1e-3, relative=1e-3))
    model.add_element(beam)
    return BTLxWriter().model_to_xml(model)


def _read(xml):
    reader = BTLxReader()
    beam = list(reader.xml_to_model(xml).elements())[0]
    assert not reader.errors
    return beam


# limits


@pytest.mark.parametrize(
    "kwargs",
    [
        {"nail_length": 0.0},
        {"cramp_width": 0.0},
        {"screw_length": -1.0},
        {"screw_diameter": 1000.1},
        {"nail_spacing": -1.0},
        {"nail_spacing": [None, 100001.0, 1.0]},
        {"cramp_angle": 180.0},
        {"cramp_angle_ref": "wall"},
    ],
)
def test_simple_contour_limits(kwargs):
    with pytest.raises(ValueError):
        SimpleContour(Polyline(PATH), **kwargs)


@pytest.mark.parametrize(
    "cls, kwargs",
    [
        (NailContour, {"contour": None}),
        (NailContour, {"contour": SimpleContour(Polyline(PATH), cramp_width=5.0)}),
        (ScrewContour, {"contour": SimpleContour(Polyline(PATH), nail_length=5.0)}),
        (PenContour, {"contour": SimpleContour(Polyline(PATH), nail_spacing=5.0)}),
        (PenContour, {"contour": SimpleContour(Polyline(PATH[:1]))}),
        (GlueArea, {"contour": SimpleContour(Polyline(PATH))}),
        (GlueArea, {"contour": SimpleContour(Polyline(SQUARE), nail_length=5.0)}),
        (GlueArea, {"contour": _closed(), "glue_amount": 0.0}),
        (PlaningArea, {"contour": _closed(), "depth": 1000.1}),
        (PlasterArea, {"contour": _closed(), "thickness": -0.1}),
        (InsulationArea, {"contour": _closed()}),
        (InsulationArea, {"contour": _closed(), "part_ref_guid": "12345678-1234-1234-1234-123456789abc"}),
        (LockoutArea, {"contour": _closed(), "for_gluing": "yes"}),
    ],
)
def test_processing_limits(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


def test_nurbs_patch_needs_a_point_per_weight():
    with pytest.raises(ValueError):
        NurbsPatch([[0.0, 0.0, 0.0]], [1.0], [0.0, 1.0], [0.0, 1.0], 1, 1, 2, 2)


# params


def test_saw_contour_params():
    params = SawContour(Contour(Polyline(SQUARE), 50.0), tool_position="left", ref_side_index=1).params

    assert params.header_attributes == {"Name": "SawContour", "Process": "yes", "Priority": "0", "ProcessID": "1", "ReferencePlaneID": "2", "ToolID": "0", "ToolPosition": "left"}
    assert list(params.as_dict()) == ["Contour"]


def test_saw_contour_params_dual_contour():
    params = SawContour(DualContour(Polyline(SQUARE), Polyline(SQUARE).translated([0, 0, -50]))).params

    assert list(params.as_dict()) == ["DualContour"]


def test_mill_contour_params():
    header = MillContour(Contour(Polyline(SQUARE), 50.0), tool_id=2, tool_position="right", counter_sink=True).params.header_attributes

    assert header["Name"] == "MillContour"
    assert header["ToolID"] == "2"
    assert header["CounterSink"] == "yes"
    assert header["ToolPosition"] == "right"


def test_nail_contour_params():
    contour = SimpleContour(Polyline(PATH), nail_length=60.0, nail_spacing=100.0)
    params = NailContour(contour=contour, tool_id=5).params

    assert params.header_attributes == {"Name": "NailContour", "Process": "yes", "Priority": "0", "ProcessID": "0", "ReferencePlaneID": "1", "ToolID": "5"}
    assert params.as_dict() == {"Contour": contour}


def test_area_params():
    params = GlueArea(contour=_closed(), glue_type="PU", glue_amount=120.0).params

    assert params.header_attributes["Name"] == "GlueArea"
    assert params.header_attributes["GlueType"] == "PU"
    assert params.header_attributes["GlueAmount"] == "120.000"
    assert list(params.as_dict()) == ["Contour"]


def test_area_params_leave_out_what_is_not_set():
    assert "Depth" not in PlaningArea(contour=_closed()).params.header_attributes
    assert "Thickness" not in PlasterArea(contour=_closed()).params.header_attributes


def test_lockout_area_params():
    header = LockoutArea(contour=_closed(), for_sawing=False).params.header_attributes

    assert header["ForSawing"] == "no"
    assert header["ForMarking"] == "yes"
    assert "ToolID" not in header


def test_insulation_area_params():
    assert InsulationArea(contour=_closed(), part_ref_guid=GUID).params.header_attributes["PartRefGUID"] == GUID


def test_free_surface_params():
    params = FreeSurface(surface=_flat_patch(-5.0), tool_id=4).params

    assert params.header_attributes == {"Name": "FreeSurface", "Process": "yes", "Priority": "0", "ProcessID": "0", "ReferencePlaneID": "1", "ToolID": "4"}


def test_simple_contour_xml():
    contour = SimpleContour(Polyline(PATH), nail_length=50.0, cramp_width=11.0, nail_spacing=[None, 80.0, 90.0], cramp_angle=30.0, cramp_angle_ref=CrampAngleRefType.GRAIN)

    assert ET.tostring(simple_contour_to_xml(contour)).decode() == (
        '<Contour NailLength="50.000" CrampWidth="11.000">'
        '<StartPoint X="10.000" Y="10.000" Z="0.000" CrampAngleRef="grain" CrampAngle="30.000" />'
        '<Line NailSpacing="80.000" CrampAngleRef="grain" CrampAngle="30.000"><EndPoint X="110.000" Y="10.000" Z="0.000" /></Line>'
        '<Line NailSpacing="90.000" CrampAngleRef="grain" CrampAngle="30.000"><EndPoint X="110.000" Y="50.000" Z="0.000" /></Line>'
        "</Contour>"
    )


def test_simple_contour_of_a_single_point_keeps_its_cramp_attributes():
    contour = SimpleContour(Polyline(PATH[:1]), cramp_angle=30.0, nail_spacing=10.0)

    assert ET.tostring(simple_contour_to_xml(contour)).decode() == '<Contour><StartPoint X="10.000" Y="10.000" Z="0.000" CrampAngle="30.000" /></Contour>'


# scale, data


def test_scale_contour():
    processing = CrampContour(contour=SimpleContour(Polyline(PATH), nail_length=50.0, cramp_width=11.0, nail_spacing=[None, 80.0, 90.0], cramp_angle=30.0)).scaled(2.0)

    assert processing.contour.polyline[1] == Point(220.0, 20.0, 0.0)
    assert processing.contour.nail_length == 100.0
    assert processing.contour.cramp_width == 22.0
    assert processing.contour.nail_spacing == [None, 160.0, 180.0]
    assert processing.contour.cramp_angle == [30.0, 30.0, 30.0]


def test_scale_area():
    area = PlaningArea(contour=_closed(), apertures=Apertures([SimpleContour(Polyline(HOLE))]), depth=2.0)

    scaled = area.scaled(10.0)

    assert scaled.depth == 20.0
    assert scaled.contour.polyline[0] == Point(1000.0, 100.0, 0.0)
    assert scaled.apertures.contours[0].polyline[0] == Point(1200.0, 200.0, 0.0)
    assert area.depth == 2.0
    assert area.contour.polyline[0] == Point(100.0, 10.0, 0.0)


def test_scale_lockout_area():
    assert LockoutArea(contour=_closed()).scaled(2.0).contour.polyline[0] == Point(200.0, 20.0, 0.0)


def test_scale_glue_amount_is_not_a_length():
    assert GlueArea(contour=_closed(), glue_amount=120.0).scaled(2.0).glue_amount == 120.0


def test_scale_saw_contour():
    scaled = SawContour(Contour(Polyline(SQUARE), 50.0)).scaled(2.0)

    assert scaled.contour_param_object.depth == 100.0
    assert scaled.contour_param_object.polyline[0] == Point(200.0, 20.0, 0.0)


def test_scale_free_surface():
    scaled = FreeSurface(surface=_flat_patch(-5.0)).scaled(2.0)

    assert scaled.surface.points[3] == Point(2000.0, 200.0, -10.0)
    assert scaled.surface.weights == [1.0] * 4


@pytest.mark.parametrize("index", range(12))
def test_json_round_trip(index):
    processing = (_material_processings() + _other_processings())[index]

    restored = json_loads(json_dumps(processing))

    assert type(restored) is type(processing)
    assert ET.tostring(_header(restored)) == ET.tostring(_header(processing))
    assert _children(restored) == _children(processing)


def _header(processing):
    return ET.Element("header", processing.params.header_attributes)


def _children(processing):
    # the reader turns the inclination of a contour into one per segment
    elements = ET.fromstring(_write("MM", processing)).find(".//{*}Processings")[0].iter()
    return [(element.tag, {key: value for key, value in element.attrib.items() if key != "Inclination"}, (element.text or "").strip()) for element in elements][1:]


# geometry


def test_saw_contour_removes_inside_with_the_tool_inside():
    # counter clockwise: left of the path is the inside
    assert TOL.is_close(_volume(SawContour(Contour(Polyline(SQUARE), 200.0), tool_position="left")), BEAM_VOLUME - 100.0 * 40.0 * 200.0)


def test_saw_contour_keeps_inside_with_the_tool_outside():
    assert TOL.is_close(_volume(SawContour(Contour(Polyline(SQUARE), 200.0), tool_position="right")), 100.0 * 40.0 * 200.0)


def test_saw_contour_removes_inside_of_clockwise_contour_with_the_tool_right():
    assert TOL.is_close(_volume(SawContour(Contour(Polyline(SQUARE[::-1]), 200.0), tool_position="right")), BEAM_VOLUME - 100.0 * 40.0 * 200.0)


def test_saw_contour_reads_back_with_the_same_side():
    beam = _read(_write("MM", SawContour(Contour(Polyline(SQUARE), 200.0), tool_position="left", ref_side_index=2)))

    assert isinstance(beam.features[0], SawContour)
    assert beam.features[0].counter_sink is True
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    assert TOL.is_close(geometry.volume, BEAM_VOLUME - 100.0 * 40.0 * 200.0)


def test_saw_contour_from_polyline_and_element():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    to_model = Transformation.from_frame(beam.ref_sides[0])

    saw = SawContour.from_polyline_and_element(Polyline(SQUARE).transformed(to_model), beam, interior=True, depth=50.0)

    assert saw.ref_side_index == 0
    assert saw.tool_position == "left"
    assert "CounterSink" not in saw.params.header_attributes
    assert TOL.is_close(_volume(saw, beam), BEAM_VOLUME - 100.0 * 40.0 * 50.0)


def test_mill_contour_from_shapes_and_element():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    to_model = Transformation.from_frame(beam.ref_sides[0])

    mill = MillContour.from_shapes_and_element(Polyline(SQUARE).transformed(to_model), beam, depth=50.0)

    assert isinstance(mill, MillContour)
    assert mill.counter_sink is True
    assert TOL.is_close(_volume(mill, beam), BEAM_VOLUME - 100.0 * 40.0 * 50.0)


@pytest.mark.parametrize("cls", [SawContour, MillContour])
def test_contour_depth_is_on_the_reference_side(cls):
    processing = cls(Contour(Polyline(SQUARE), 50.0), tool_position="left", counter_sink=True)

    # RS1 is the side at z = -100, and its y axis points to -y
    assert TOL.is_zero(_volume_in_box(processing, [100.0, 0.0, -100.0], [200.0, 40.0, -50.0]))
    assert _volume_in_box(processing, [100.0, 0.0, -50.0], [200.0, 40.0, 100.0]) == pytest.approx(100.0 * 40.0 * 150.0, rel=1e-4)  # Contour adds 0.001 to the depth


@pytest.mark.parametrize("depth", [0.0, 140.0])
def test_contour_which_is_not_depth_bounded_goes_through(depth):
    contour = Contour(Polyline(SQUARE), depth, depth_bounded=False)

    assert TOL.is_close(_volume(MillContour(contour, counter_sink=True, tool_position="left")), BEAM_VOLUME - 100.0 * 40.0 * 200.0)
    assert contour.depth == depth


def test_contour_with_inclination_narrows_towards_the_tool_side():
    # the figure: a positive inclination tilts the cut to the side of the tool, which is the inside of this hole
    offset = 50.0 * math.tan(math.radians(10.0))
    top, middle, bottom = 100.0 * 40.0, (100.0 - offset) * (40.0 - offset), (100.0 - 2 * offset) * (40.0 - 2 * offset)
    frustum = 50.0 / 6.0 * (top + 4 * middle + bottom)

    volume = _volume(MillContour(Contour(Polyline(SQUARE), 50.0, inclination=[10.0]), counter_sink=True, tool_position="left"))

    assert volume == pytest.approx(BEAM_VOLUME - frustum, rel=1e-6)


def test_contour_which_gives_no_solid_is_reported():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features([MillContour(Contour(Polyline(SQUARE), 200.0, inclination=[10.0]), counter_sink=True, tool_position="left")])

    beam.compute_elementgeometry(include_features=True)

    assert len(beam.debug_info) == 1


@pytest.mark.parametrize("cls", [SawContour, MillContour])
def test_open_contour_is_reported(cls):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features([cls(Contour(Polyline(PATH), 50.0), tool_position="left")])

    geometry = beam.compute_elementgeometry(include_features=True)

    assert len(beam.debug_info) == 1
    assert TOL.is_close(geometry.volume, BEAM_VOLUME)


def test_planing_area():
    area = PlaningArea(contour=_closed(), depth=5.0)

    assert TOL.is_close(_volume(area), BEAM_VOLUME - 100.0 * 40.0 * 5.0)


def test_planing_area_is_on_the_reference_side():
    # RS1 is the side at z = -100
    area = PlaningArea(contour=_closed(), depth=5.0)

    assert TOL.is_zero(_volume_in_box(area, [100.0, 0.0, -100.0], [200.0, 40.0, -95.0]))
    assert TOL.is_close(_volume_in_box(area, [100.0, -50.0, -100.0], [200.0, 0.0, -95.0]), 100.0 * 50.0 * 5.0)


def test_planing_area_ref_side_3():
    # RS3 is the side at z = 100, and its y axis points to y
    area = PlaningArea(contour=_closed(), depth=5.0, ref_side_index=2)

    assert TOL.is_zero(_volume_in_box(area, [100.0, -40.0, 95.0], [200.0, 0.0, 100.0]))
    assert TOL.is_close(_volume_in_box(area, [100.0, 0.0, 95.0], [200.0, 50.0, 100.0]), 100.0 * 50.0 * 5.0)


def test_planing_area_with_aperture():
    area = PlaningArea(contour=_closed(), apertures=Apertures([SimpleContour(Polyline(HOLE))]), depth=5.0)

    assert TOL.is_close(_volume(area), BEAM_VOLUME - (100.0 * 40.0 - 20.0 * 20.0) * 5.0)


def test_planing_area_without_depth_removes_nothing():
    assert TOL.is_close(_volume(PlaningArea(contour=_closed())), BEAM_VOLUME)


def test_planing_area_from_polyline_and_element():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    to_model = Transformation.from_frame(beam.ref_sides[1])

    area = PlaningArea.from_polyline_and_element(Polyline(SQUARE).transformed(to_model), beam, apertures=[Polyline(HOLE).transformed(to_model)], depth=5.0)

    assert area.ref_side_index == 1
    assert area.contour.polyline[0] == Point(*SQUARE[0])
    assert area.apertures.contours[0].polyline[0] == Point(*HOLE[0])
    assert TOL.is_close(_volume(area, beam), BEAM_VOLUME - (100.0 * 40.0 - 20.0 * 20.0) * 5.0)


def test_from_polyline_and_element_splits_contour_and_processing_attributes():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    polyline = Polyline(PATH).transformed(Transformation.from_frame(beam.ref_sides[3]))

    nail = NailContour.from_shapes_and_element(polyline, beam, nail_length=60.0, nail_spacing=100.0, tool_id=2)

    assert nail.ref_side_index == 3
    assert nail.tool_id == 2
    assert nail.contour.nail_length == 60.0
    assert nail.contour.nail_spacing == [100.0, 100.0, 100.0]
    assert nail.contour.polyline[1] == Point(*PATH[1])


def test_from_polyline_and_element_with_two_points():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)

    pen = PenContour.from_polyline_and_element(Polyline(PATH[:2]).transformed(Transformation.from_frame(beam.ref_sides[1])), beam)

    assert pen.ref_side_index == 1


def test_from_polyline_and_element_off_the_sides():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)

    with pytest.raises(ValueError):
        PenContour.from_polyline_and_element(Polyline([[10.0, 0.0, 0.0], [20.0, 0.0, 0.0]]), beam)


@pytest.mark.parametrize("index", range(8))
def test_other_processings_leave_the_geometry(index):
    assert TOL.is_close(_volume(_other_processings()[index]), BEAM_VOLUME)


def test_free_surface_flat():
    # z is measured along the normal of the reference side, so the layer is removed down from it
    assert TOL.is_close(_volume(FreeSurface(surface=_flat_patch(-20.0))), BEAM_VOLUME - 1000.0 * 100.0 * 20.0)


def test_free_surface_is_on_the_reference_side():
    surface = FreeSurface(surface=_flat_patch(-20.0, x=(100.0, 300.0), y=(0.0, 50.0)))

    assert TOL.is_zero(_volume_in_box(surface, [100.0, 0.0, -100.0], [300.0, 50.0, -80.0]))
    assert TOL.is_close(_volume_in_box(surface, [100.0, -50.0, -100.0], [300.0, 0.0, -80.0]), 200.0 * 50.0 * 20.0)


def test_free_surface_ref_side_3():
    surface = FreeSurface(surface=_flat_patch(-20.0, x=(100.0, 300.0), y=(0.0, 50.0)), ref_side_index=2)

    assert TOL.is_zero(_volume_in_box(surface, [100.0, -50.0, 80.0], [300.0, 0.0, 100.0]))
    assert TOL.is_close(_volume_in_box(surface, [100.0, 0.0, 80.0], [300.0, 50.0, 100.0]), 200.0 * 50.0 * 20.0)


def test_free_surface_is_independent_of_the_direction_of_v():
    points = [[0.0, 100.0, -20.0], [1000.0, 100.0, -20.0], [0.0, 0.0, -20.0], [1000.0, 0.0, -20.0]]
    surface = FreeSurface(surface=NurbsPatch(points, [1.0] * 4, [0.0, 1.0], [0.0, 1.0], 1, 1, 2, 2))

    assert TOL.is_close(_volume(surface), BEAM_VOLUME - 1000.0 * 100.0 * 20.0)


def test_free_surface_slope():
    points = [[0.0, 0.0, 0.0], [1000.0, 0.0, -40.0], [0.0, 100.0, 0.0], [1000.0, 100.0, -40.0]]
    surface = FreeSurface(surface=NurbsPatch(points, [1.0] * 4, [0.0, 1.0], [0.0, 1.0], 1, 1, 2, 2))

    assert TOL.is_close(_volume(surface), BEAM_VOLUME - 1000.0 * 100.0 * 20.0)


def test_free_surface_curved_with_different_counts():
    # degree 2 in U: z(t) = -80 t (1 - t) on the curve, whose average is -80 / 6. The order of the points is row wise.
    points = [[0.0, 0.0, 0.0], [500.0, 0.0, -40.0], [1000.0, 0.0, 0.0], [0.0, 100.0, 0.0], [500.0, 100.0, -40.0], [1000.0, 100.0, 0.0]]
    surface = FreeSurface(surface=NurbsPatch(points, [1.0] * 6, [0.0, 0.0, 1.0, 1.0], [0.0, 1.0], 2, 1, 3, 2))

    assert TOL.is_close(_volume(surface), BEAM_VOLUME - 1000.0 * 100.0 * 80.0 / 6.0)


def test_nurbs_patch_knots_of_the_figure():
    # 10 x 2 points, degree 3 in U, the knot vector of the example of the BTLx manual
    points = [[10.0 * u, 100.0 * v, 0.0] for v in range(2) for u in range(10)]
    knots_u = [0.0, 0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 4.0]

    surface = NurbsPatch(points, [1.0] * 20, knots_u, [0.0, 1.0], 3, 1, 10, 2).to_surface()

    assert surface.knots_u == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert surface.mults_u == [4, 2, 2, 2, 4]
    assert surface.point_at(4.0, 1.0) == Point(90.0, 100.0, 0.0)


def test_nurbs_patch_knots_of_the_schema_and_a_full_vector():
    points = [[10.0 * u, 100.0 * v, 0.0] for v in range(2) for u in range(3)]

    for knots_u in ([0.0, 0.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]):
        assert NurbsPatch(points, [1.0] * 6, knots_u, [0.0, 1.0], 2, 1, 3, 2).to_surface().mults_u == [3, 3]


def test_free_surface_from_surface_and_element():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    to_model = Transformation.from_frame(beam.ref_sides[2])
    points = [[[0.0, 0.0, -20.0], [0.0, 100.0, -20.0]], [[500.0, 0.0, -20.0], [500.0, 100.0, -20.0]], [[1000.0, 0.0, -20.0], [1000.0, 100.0, -20.0]]]
    surface = NurbsSurface.from_parameters([[Point(*p) for p in column] for column in points], [[1.0, 1.0]] * 3, [0.0, 1.0], [0.0, 1.0], [3, 3], [2, 2], 2, 1)

    processing = FreeSurface.from_shapes_and_element(surface.transformed(to_model), beam, ref_side_index=2)

    assert processing.ref_side_index == 2
    assert processing.surface.points[1] == Point(500.0, 0.0, -20.0)
    assert processing.surface.points[3] == Point(0.0, 100.0, -20.0)
    assert processing.surface.knots_u == [0.0, 0.0, 1.0, 1.0]
    assert TOL.is_close(_volume(processing, beam), BEAM_VOLUME - 1000.0 * 100.0 * 20.0)


# BTLx


@pytest.mark.parametrize("index", range(12))
def test_btlx_round_trip(index):
    processing = (_material_processings() + _other_processings())[index]

    restored = _read(_write("MM", processing)).features[0]

    assert type(restored) is type(processing)
    assert _header(restored).attrib == _header(processing).attrib
    assert _children(restored) == _children(processing)


def test_btlx_round_trip_keeps_contour_attributes():
    cramp = CrampContour(contour=SimpleContour(Polyline(PATH), nail_length=50.0, cramp_width=11.0, nail_spacing=[None, 80.0, 90.0], cramp_angle=30.0, cramp_angle_ref="grain"))

    restored = _read(_write("MM", cramp)).features[0].contour

    assert restored.nail_length == 50.0
    assert restored.cramp_width == 11.0
    assert restored.nail_spacing == [None, 80.0, 90.0]
    assert restored.cramp_angle == [30.0, 30.0, 30.0]
    assert restored.cramp_angle_ref == ["grain", "grain", "grain"]


def test_btlx_round_trip_keeps_processing_attributes():
    processings = _read(_write("MM", *_other_processings())).features

    assert processings[4].glue_type == "PU"
    assert processings[4].glue_amount == 120.0
    assert len(processings[4].apertures.contours) == 1
    assert processings[5].thickness == 15.0
    assert processings[6].part_ref_guid == GUID
    assert processings[7].for_sawing is False
    assert processings[7].for_milling is True


def test_btlx_is_written_in_millimeters():
    xml = _write("M", PlaningArea(contour=_closed(), depth=0.5))

    assert 'Depth="500.000"' in xml
    assert 'X="100000.000"' in xml


def test_btlx_arc_is_a_parsing_error():
    xml = _write("MM", PenContour(contour=SimpleContour(Polyline(PATH))))
    xml = xml.replace("<Line>", "<Arc><PointOnArc X='0' Y='0' Z='0'/>", 1).replace("</Line>", "</Arc>", 1)

    reader = BTLxReader()
    beam = list(reader.xml_to_model(xml).elements())[0]

    assert not beam.features
    assert "not supported" in str(reader.errors[0])
