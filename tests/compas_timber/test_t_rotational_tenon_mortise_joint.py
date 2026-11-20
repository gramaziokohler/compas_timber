import json
import math
import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import distance_point_line
from compas_brep import Brep
from compas_brep.curves import NurbsCurve

from compas_timber.connections import EndMillType
from compas_timber.connections import RotationalTenonProfile
from compas_timber.connections import TRotationalTenonMortiseJoint
from compas_timber.elements import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import DualContour
from compas_timber.fabrication import NurbsContour
from compas_timber.fabrication import TenonShapeType
from compas_timber.fabrication.btlx import nurbs_contour_to_xml
from compas_timber.model import TimberModel

# main beam along y onto the cross beam's face at y = 80: 120 wide (along x), 160 thick (along z);
# cross beam along x: 160 deep, 160 high; centerlines in the plane z = 0
MAIN_WIDTH, MAIN_THICKNESS, CROSS_SIZE = 120.0, 160.0, 160.0
SHOULDER_Y = CROSS_SIZE / 2


def build(angle=90.0, tilt=0.0, cross_height=CROSS_SIZE, **kwargs):
    model = TimberModel()
    a, t = math.radians(angle), math.radians(tilt)
    direction = Vector(math.cos(a) * math.cos(t), math.sin(a) * math.cos(t), math.sin(t))
    main = Beam.from_centerline(Line(Point(0, 0, 0) + direction * 900, Point(0, 0, 0)), width=MAIN_WIDTH, height=MAIN_THICKNESS, z_vector=Vector(0, 0, 1))
    cross = Beam.from_centerline(Line(Point(-700, 0, 0), Point(700, 0, 0)), width=CROSS_SIZE, height=cross_height, z_vector=Vector(0, 0, 1))
    model.add_element(main)
    model.add_element(cross)
    joint = TRotationalTenonMortiseJoint.create(model, main, cross, **kwargs)
    errors = model.process_joinery()
    return model, joint, main, cross, errors


def overlap(a, b):
    try:
        result = Brep.from_boolean_intersection(a, b)
    except Exception:
        return 0.0
    if isinstance(result, list):
        return sum(abs(r.volume) for r in result)
    return abs(result.volume) if result is not None else 0.0


def tenon_volume(main, cross):
    """The part of the main beam inside of the cross beam."""
    return overlap(main.geometry, Brep.from_box(cross.blank))


def faceting(main, cross, factor=2e-4):
    """How much a tenon and its mortise may overlap because their arcs are tessellated in the geometry."""
    return factor * tenon_volume(main, cross)


def parallel_round_tenon_area(joint):
    """Area of a parallel tenon with a round tip, in the main beam's cross section: an annular sector plus a half disc."""
    half = joint.width / 2.0
    sweep = math.asin((joint.height - half) / joint.rotation_radius)
    return sweep * joint.rotation_radius * joint.width + math.pi * half**2 / 2.0


def up(joint):
    """The direction the mortise opens to: the normal of the main beam's face the tenon starts from."""
    return joint.main_beam.ref_sides[joint.main_ref_side_index].normal


def swings_out(joint, main, cross, angles=(5.0, 30.0, 60.0, 90.0), factor=2e-4):
    tolerance = faceting(main, cross, factor)
    axis = joint.rotation_axis
    if overlap(main.geometry, cross.geometry) > tolerance:
        return False
    for angle in angles:
        swung = main.geometry.transformed(Rotation.from_axis_and_angle(axis.direction, math.radians(angle), point=axis.start))
        if overlap(swung, cross.geometry) > tolerance:
            return False
    return True


def mortise_flank_radii(joint, cross):
    """(min, max) distance from the rotation axis of each NURBS segment of the mortise's contour."""
    contour = cross.features[0].contour_param_object
    ref_side = cross.ref_sides[cross.features[0].ref_side_index]
    axis = joint.rotation_axis
    radii = []
    for curve in [s for s in contour.segments if isinstance(s, NurbsCurve)]:
        model_curve = curve.transformed(Transformation.from_frame(ref_side))
        start, end = model_curve.domain
        distances = [distance_point_line(model_curve.point_at(start + (end - start) * i / 20), axis) for i in range(21)]
        radii.append((min(distances), max(distances)))
    return radii


@pytest.fixture(scope="module")
def default_joint():
    model, joint, main, cross, errors = build()
    assert not errors
    return joint, main, cross


@pytest.fixture(scope="module")
def dovetail_joint():
    model, joint, main, cross, errors = build(end_mill=EndMillType.DOVETAIL)
    assert not errors
    return joint, main, cross


########################################################################
# Parameters
########################################################################


def test_defaults(default_joint):
    joint, _, _ = default_joint

    assert joint.width == MAIN_WIDTH / 2
    assert joint.rotation_radius == MAIN_WIDTH
    assert joint.height == pytest.approx(MAIN_WIDTH * math.sin(math.radians(45.0)) + joint.width / 2)  # the tip 45 degrees around the axis
    # between the tip just touching the side towards the axis (about 5.2) and the outer flank flush with the other (30)
    assert 5.1 < joint.start_y < (MAIN_WIDTH - joint.width) / 2
    assert joint.start_depth == 0.0
    assert joint.length == 0.75 * CROSS_SIZE
    assert joint.rotation in (0.0, 180.0)
    assert joint.tenon_shape == TenonShapeType.ROUND
    assert joint.profile == RotationalTenonProfile.PARALLEL
    assert joint.start_width == 1.5 * joint.width
    assert joint.end_mill == EndMillType.FLAT
    assert joint.tool_angle == 15.0
    assert joint.axis_offset == 0.0
    assert joint.tool_diameter is None
    assert joint.shape_radius == joint.width / 4


def test_mortise_opens_upwards_by_default(default_joint):
    joint, _, _ = default_joint

    assert up(joint).z == pytest.approx(1.0)
    assert joint.rotation_axis.start.z == pytest.approx(MAIN_THICKNESS / 2)


def test_dovetail_length_defaults_to_what_fits_in_the_main_beam(dovetail_joint):
    joint, main, cross = dovetail_joint

    assert joint.length < 0.75 * CROSS_SIZE
    assert not main.debug_info and not cross.debug_info


def test_rotation_axis_runs_along_the_main_beam_from_the_shoulder(default_joint):
    joint, main, _ = default_joint
    axis = joint.rotation_axis

    assert axis.direction.y == pytest.approx(1.0)  # square to the shoulder, along the main beam away from the cross beam
    assert axis.start.y == pytest.approx(SHOULDER_Y)
    assert axis.start.z == pytest.approx(MAIN_THICKNESS / 2)  # where the tenon starts: flush with the main beam's face
    assert abs(axis.start.x) == pytest.approx(joint.rotation_radius - joint.start_y)  # beside the tenon's centerline


def test_check_elements_compatibility():
    for angle in (90.0, 70.0, 110.0):
        _, _, main, cross, _ = build(angle=angle)
        assert TRotationalTenonMortiseJoint.check_elements_compatibility([main, cross])

    _, _, tilted, cross, _ = build(tilt=25.0)
    assert not TRotationalTenonMortiseJoint.check_elements_compatibility([tilted, cross])
    with pytest.raises(BeamJoiningError):
        TRotationalTenonMortiseJoint.check_elements_compatibility([tilted, cross], raise_error=True)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(tilt=25.0),  # the cross beam has no face parallel to the plane of the beams
        dict(rotation=45.0),
        dict(rotation=90.0),
        dict(rotation_radius=20.0),  # not more than half the width of the tenon
        dict(height=500.0),  # more than a quarter turn around the axis
        dict(start_y=-200.0),  # the tenon does not start within the main beam
        dict(width=100.0, start_y=0.0),  # the tenon hooks out of the main beam's side
        dict(start_depth=60.0, height=120.0),  # out of the main beam's opposite face
        dict(profile=RotationalTenonProfile.CONICAL, start_width=20.0),  # narrower where it starts than at the tip
        dict(cross_height=400.0),  # the cross beam reaches so far above the axis that the tenon cannot get out
        dict(axis_offset=100.0),  # so far above the start that the inner flank does not reach it
    ],
)
def test_invalid_layouts_and_parameters_are_reported(kwargs):
    _, _, _, _, errors = build(**kwargs)

    assert errors  # reported while extending the beams, and again while adding the features
    assert all(isinstance(error, BeamJoiningError) for error in errors)


########################################################################
# Processings
########################################################################


def test_features(default_joint):
    joint, main, cross = default_joint

    assert len(cross.features) == 1
    mortise = cross.features[0]
    assert isinstance(mortise, FreeContour)
    assert isinstance(mortise.contour_param_object, NurbsContour)
    assert mortise.counter_sink
    assert mortise.ref_side_index == joint.cross_face_index  # milled into the shoulder
    assert mortise.contour_param_object.depth == pytest.approx(joint.length)

    assert len(main.features) == 1  # the main beam was extended to the end of the tenon, which is milled out of it
    tenon_cut = main.features[0]
    assert isinstance(tenon_cut.contour_param_object, NurbsContour)
    assert tenon_cut.ref_side_index == joint.main_end_side_index
    assert tenon_cut.ref_side_index in (4, 5)
    assert tenon_cut.contour_param_object.depth == pytest.approx(joint.length)
    assert joint.features == [mortise, tenon_cut]


def test_mortise_btlx_contour_is_made_of_exact_arcs(default_joint):
    joint, _, cross = default_joint
    contour = cross.features[0].contour_param_object

    root = nurbs_contour_to_xml(contour)
    # outer flank, tip, inner flank, each continued around the axis out of the cross beam, closed outside of it
    assert [child.tag for child in root] == ["StartPoint", "NURBS", "NURBS", "NURBS", "Line"]
    assert all(nurbs.attrib["Degree"] == "2" for nurbs in root.findall("NURBS"))
    assert float(root.attrib["Inclination"]) == 0.0
    assert float(root.attrib["Depth"]) == pytest.approx(joint.length)

    # the flanks lie exactly on circles around the rotation axis
    outer, _, inner = mortise_flank_radii(joint, cross)
    assert outer[1] - outer[0] < 1e-6 and outer[0] == pytest.approx(joint.rotation_radius + joint.width / 2)
    assert inner[1] - inner[0] < 1e-6 and inner[0] == pytest.approx(joint.rotation_radius - joint.width / 2)


def test_btlx_mills_the_tenon_from_the_main_beams_end(default_joint):
    joint, main, cross = default_joint
    model = joint.main_beam.model

    root = ET.fromstring(BTLxWriter().model_to_xml(model))
    planes = sorted(int(element.attrib["ReferencePlaneID"]) for element in root.iter() if element.tag.endswith("FreeContour"))
    assert planes == sorted([joint.cross_face_index + 1, joint.main_end_side_index + 1])


def test_dovetail_end_mill_inclines_the_walls(dovetail_joint):
    joint, main, cross = dovetail_joint

    mortise = nurbs_contour_to_xml(cross.features[0].contour_param_object)
    assert abs(float(mortise.attrib["Inclination"])) == pytest.approx(joint.tool_angle)

    # the walls of the tenon incline, as do their straight continuations out of the main beam; the region around it does not
    tenon_cut = nurbs_contour_to_xml(next(f for f in main.features if isinstance(f, FreeContour)).contour_param_object)
    inclinations = [abs(float(segment.attrib["Inclination"])) for segment in tenon_cut if segment.tag != "StartPoint"]
    assert sorted(set(inclinations)) == pytest.approx([0.0, joint.tool_angle])
    inclined = [segment.tag for segment in tenon_cut if segment.tag != "StartPoint" and float(segment.attrib["Inclination"]) != 0.0]
    assert inclined == ["Line", "NURBS", "NURBS", "NURBS", "Line"]

    # the mortise is wider at its bottom than at the face: larger than one as deep cut with a flat end mill
    _, _, _, flat_cross, _ = build(length=joint.length, start_y=joint.start_y)
    pocket = Brep.from_box(cross.blank).volume - cross.geometry.volume
    flat_pocket = Brep.from_box(flat_cross.blank).volume - flat_cross.geometry.volume
    assert pocket > flat_pocket * 1.05


def test_a_main_beam_reaching_past_the_tenon_is_cut_off_at_its_end():
    _, joint, main, cross, errors = build(length=40.0)  # the main beam's centerline ends 80 into the cross beam

    assert not errors
    assert isinstance(main.features[0], JackRafterCutProxy)
    assert main.features[1].contour_param_object.depth == pytest.approx(SHOULDER_Y)  # milled from the blank's end
    assert tenon_volume(main, cross) == pytest.approx(parallel_round_tenon_area(joint) * 40.0, rel=5e-3)


########################################################################
# Geometry and assembly
########################################################################


def test_tenon_volume(default_joint):
    joint, main, cross = default_joint
    expected = parallel_round_tenon_area(joint) * joint.length

    assert tenon_volume(main, cross) == pytest.approx(expected, rel=5e-3)


def test_tenon_fits_and_swings_out_about_the_rotation_axis(default_joint):
    joint, main, cross = default_joint

    assert swings_out(joint, main, cross)


def test_the_hook_blocks_pulling_the_tenon_out_of_the_face_or_sideways(default_joint):
    joint, main, cross = default_joint
    tolerance = faceting(main, cross)

    for direction in (up(joint), Vector(1, 0, 0), Vector(-1, 0, 0)):
        pulled = main.geometry.transformed(Translation.from_vector(direction * 20))
        assert overlap(pulled, cross.geometry) > 100 * tolerance


def test_flat_end_mill_lets_the_main_beam_be_pulled_back_dovetail_does_not(default_joint, dovetail_joint):
    for (joint, main, cross), locked in ((default_joint, False), (dovetail_joint, True)):
        pulled = main.geometry.transformed(Translation.from_vector(joint.rotation_axis.direction * 20))
        stuck = overlap(pulled, cross.geometry) > 1e-2 * tenon_volume(main, cross)
        assert stuck == locked


def test_dovetail_tenon_fits_and_swings_out(dovetail_joint):
    joint, main, cross = dovetail_joint

    assert swings_out(joint, main, cross)


def test_conical_tenon_narrows_on_both_flanks_from_its_start_to_its_tip():
    _, joint, main, cross, errors = build(profile=RotationalTenonProfile.CONICAL, start_width=80.0)
    assert not errors

    outline = joint._outline(0.0)
    outer, inner = outline.start_points
    axis_u = joint.start_y - joint.rotation_radius
    assert outer[0] - inner[0] == pytest.approx(80.0)
    # wider by the same on both sides of the circle around the axis
    assert outer[0] - axis_u - joint.rotation_radius == pytest.approx(40.0)
    assert joint.rotation_radius - (inner[0] - axis_u) == pytest.approx(40.0)
    # the flanks' circles: the outer one centered above the axis, the inner one below it (v points down)
    outer_center, inner_center = outline.flank_centers
    assert outer_center[1] < 0.0 < inner_center[1]
    tip = outline.segments[1]
    assert math.hypot(tip.start[0] - tip.center[0], tip.start[1] - tip.center[1]) == pytest.approx(joint.width / 2)

    assert swings_out(joint, main, cross)
    pulled = main.geometry.transformed(Translation.from_vector(up(joint) * 20))
    assert overlap(pulled, cross.geometry) > 100 * faceting(main, cross)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(tool_diameter=70.0),  # wider than the mortise, 60
        dict(tool_diameter=20.0, tenon_shape=TenonShapeType.SQUARE),  # its square corners cannot be milled
        dict(tool_diameter=20.0, tenon_shape=TenonShapeType.RADIUS, shape_radius=5.0),  # corners tighter than the tool
    ],
)
def test_tool_diameter_reports_what_cannot_be_milled(kwargs):
    _, _, _, _, errors = build(**kwargs)

    assert errors
    assert all(isinstance(error, BeamJoiningError) and "tool_diameter" in error.debug_info for error in errors)


def test_tool_diameter_which_fits():
    _, joint, _, _, errors = build(tool_diameter=20.0, tenon_shape=TenonShapeType.RADIUS)
    assert not errors
    assert joint.shape_radius == 10.0  # the corners of the tip default to the tool's radius

    _, _, _, _, errors = build(tool_diameter=MAIN_WIDTH / 2)  # exactly as wide as the mortise
    assert not errors


@pytest.mark.parametrize("tip", [TenonShapeType.SQUARE, TenonShapeType.RADIUS])
@pytest.mark.parametrize("end_mill", [EndMillType.FLAT, EndMillType.DOVETAIL])
def test_square_and_radius_tips(tip, end_mill):
    _, joint, main, cross, errors = build(tenon_shape=tip, end_mill=end_mill)

    assert not errors
    assert not main.debug_info and not cross.debug_info
    # Where inclined walls of a tessellated arc and a line meet at a sharp corner, the geometry carries on the arc's
    # last straight segment past its end, so the corners of a square tip's dovetail mortise come out a little small
    # (up to about 1 mm) in the geometry. The BTLx holds the exact arcs.
    factor = 5e-4 if (tip, end_mill) == (TenonShapeType.SQUARE, EndMillType.DOVETAIL) else 2e-4
    assert swings_out(joint, main, cross, angles=(30.0,), factor=factor)


def test_rotation_180_turns_the_joint_about_the_main_beam(default_joint):
    joint, _, _ = default_joint
    _, turned, _, _, errors = build(rotation=180.0 - joint.rotation)

    assert not errors
    assert turned.start_y == pytest.approx(joint.start_y)
    assert turned.rotation_axis.start.x == pytest.approx(-joint.rotation_axis.start.x)
    assert turned.rotation_axis.start.z == pytest.approx(-joint.rotation_axis.start.z)


def test_start_depth_sinks_the_tenon_and_the_axis_below_the_face():
    _, joint, main, cross, errors = build(start_depth=20.0)

    assert not errors
    assert joint.rotation_axis.start.z == pytest.approx(MAIN_THICKNESS / 2 - 20.0)
    assert len(main.features) == 2  # and the main beam's face down to the tenon
    assert tenon_volume(main, cross) == pytest.approx(parallel_round_tenon_area(joint) * joint.length, rel=5e-3)
    assert swings_out(joint, main, cross)  # the mortise follows the tenon's path up past the axis


def test_a_cross_beam_reaching_above_the_main_beam():
    _, joint, main, cross, errors = build(cross_height=200.0)

    assert not errors
    assert swings_out(joint, main, cross)


@pytest.mark.parametrize("axis_offset", [30.0, -30.0])
def test_axis_offset_moves_the_axis_square_to_the_face(axis_offset):
    _, joint, main, cross, errors = build(axis_offset=axis_offset)

    assert not errors
    assert joint.rotation_axis.start.z == pytest.approx(MAIN_THICKNESS / 2 + axis_offset)
    assert joint.rotation_axis.start.y == pytest.approx(SHOULDER_Y)
    assert joint.rotation_axis.start.x == pytest.approx(joint.rotation_radius - joint.start_y)  # still start_y - rotation_radius across

    # the tenon still starts at the main beam's face, its flanks crossing it at an angle, and arcs around the axis
    outer, inner = joint._outline(0.0).start_points
    axis_u = joint.start_y - joint.rotation_radius
    assert outer == pytest.approx((axis_u + math.sqrt((joint.rotation_radius + joint.width / 2) ** 2 - axis_offset**2), 0.0))
    assert inner == pytest.approx((axis_u + math.sqrt((joint.rotation_radius - joint.width / 2) ** 2 - axis_offset**2), 0.0))
    (outer_radii, _, inner_radii) = mortise_flank_radii(joint, cross)
    assert outer_radii == pytest.approx((joint.rotation_radius + joint.width / 2,) * 2)
    assert inner_radii == pytest.approx((joint.rotation_radius - joint.width / 2,) * 2)

    assert swings_out(joint, main, cross)
    pulled = main.geometry.transformed(Translation.from_vector(up(joint) * 20))
    assert overlap(pulled, cross.geometry) > 100 * faceting(main, cross)


@pytest.mark.parametrize("end_mill", [EndMillType.DOVETAIL])
@pytest.mark.parametrize("profile", [RotationalTenonProfile.PARALLEL, RotationalTenonProfile.CONICAL])
def test_offset_axis_with_other_profiles_and_end_mills(profile, end_mill):
    for axis_offset in (25.0, -25.0):
        _, joint, main, cross, errors = build(axis_offset=axis_offset, profile=profile, end_mill=end_mill)

        assert not errors
        assert swings_out(joint, main, cross, angles=(30.0,))


def test_release_angle_brings_the_tenon_out_of_the_cross_beam(default_joint):
    joint, main, cross = default_joint
    axis = joint.rotation_axis
    blank = Brep.from_box(cross.blank)

    def turned(angle):
        return main.geometry.transformed(Rotation.from_axis_and_angle(axis.direction, math.radians(angle), point=axis.start))

    assert 0.0 < joint.release_angle < 90.0
    assert overlap(turned(joint.release_angle - 5.0), blank) > 1.0
    assert overlap(turned(joint.release_angle + 1.0), blank) < 1e-6


def test_return_angle_is_where_the_tenon_comes_round_to_the_cross_beam_again():
    _, joint, main, cross, errors = build(axis_offset=-60.0)  # the cross beam's face 60 above the axis
    axis = joint.rotation_axis

    def turned(angle):
        return main.geometry.transformed(Rotation.from_axis_and_angle(axis.direction, math.radians(angle), point=axis.start))

    assert not errors
    assert joint.release_angle < joint.return_angle < 180.0
    assert overlap(turned(joint.return_angle - 2.0), cross.geometry) < faceting(main, cross)
    assert overlap(turned(joint.return_angle + 10.0), cross.geometry) > 10 * faceting(main, cross)


########################################################################
# Main beam at an angle
########################################################################


def outline_area_and_centroid_u(joint):
    """Area of the tenon in the main beam's cross section, and how far across the main beam its centroid lies."""
    points = []
    for segment in joint._outline(0.0).segments:
        points += segment.sample(64)[:-1]
    area = moment = 0.0
    for (u0, v0), (u1, v1) in zip(points, points[1:] + points[:1]):
        cross_product = u0 * v1 - u1 * v0
        area += cross_product / 2.0
        moment += (u0 + u1) * cross_product / 6.0
    return abs(area), moment / area


@pytest.mark.parametrize("angle", [70.0, 110.0])
def test_angled_main_beam_turns_about_an_axis_along_it_and_is_flush_with_the_cross_beam(angle):
    _, joint, main, cross, errors = build(angle=angle)
    assert not errors

    # the whole main beam turns about one axis, along it, on the side of the acute angle
    axis = joint.rotation_axis
    direction = main.centerline.direction.unitized()
    assert abs(axis.direction.dot(direction)) == pytest.approx(1.0)
    beside = Vector.from_start_end(main.centerline.closest_point(axis.start), axis.start)
    acute_side = 1.0 if angle < 90.0 else -1.0  # the main beam comes in from +x at 70 degrees, from -x at 110
    assert beside.x * acute_side > 0

    # one FreeContour of two contours each: the mortise, from the cross beam's face down to the end of the tenon, and
    # the waste around the tenon, from the main beam's end down to the slanted shoulder
    assert [type(feature) for feature in cross.features] == [FreeContour]
    assert [type(feature) for feature in main.features] == [FreeContour]
    assert isinstance(cross.features[0].contour_param_object, DualContour)
    assert isinstance(main.features[0].contour_param_object, DualContour)
    assert cross.features[0].ref_side_index == joint.cross_face_index
    assert main.features[0].ref_side_index == joint.main_end_side_index

    # only the tenon reaches into the cross beam, longer on the side of the acute angle...
    area, centroid_u = outline_area_and_centroid_u(joint)
    slope = 1.0 / math.tan(math.radians(min(angle, 180.0 - angle)))  # how much further the face lies, per unit across
    assert tenon_volume(main, cross) == pytest.approx(area * (joint.length - slope * centroid_u), rel=5e-3)
    # ...and the rest of the main beam's end is flush with the cross beam's face
    far_end_to_face = 900.0 - SHOULDER_Y / math.sin(math.radians(angle))  # along the main beam's centerline
    assert main.geometry.volume == pytest.approx(MAIN_WIDTH * MAIN_THICKNESS * far_end_to_face + tenon_volume(main, cross), rel=1e-3)
    # the mortise is the tenon's shape, with no gap around it (its path out lies above the cross beam)
    assert Brep.from_box(cross.blank).volume - cross.geometry.volume == pytest.approx(tenon_volume(main, cross), rel=1e-3)

    assert swings_out(joint, main, cross)
    pulled = main.geometry.transformed(Translation.from_vector(up(joint) * 20))
    assert overlap(pulled, cross.geometry) > 100 * faceting(main, cross)


def test_angled_mortise_walls_follow_the_main_beam_and_its_bottom_is_the_tenons_end():
    _, joint, main, cross, errors = build(angle=70.0)
    assert not errors

    contour = cross.features[0].contour_param_object
    to_model = Transformation.from_frame(cross.ref_sides[joint.cross_face_index])
    face = [point.transformed(to_model) for point in contour.principal_contour.points]
    bottom = [point.transformed(to_model) for point in contour.associated_contour.points]
    direction = main.centerline.direction.unitized()
    for a, b in zip(face, bottom):
        wall = Vector.from_start_end(a, b)
        assert wall.cross(direction).length == pytest.approx(0.0, abs=1e-6 * max(wall.length, 1.0))  # along the main beam
        # on the tenon's square end, as far along the main beam from the shoulder as the length of the tenon
        assert abs(Vector.from_start_end(joint.rotation_axis.start, b).dot(direction)) == pytest.approx(joint.length)
    lengths = [Vector.from_start_end(a, b).length for a, b in zip(face, bottom)]
    assert max(lengths) - min(lengths) > 10.0  # deeper on the side of the acute angle, as the tenon is longer there

    root = ET.fromstring(BTLxWriter().model_to_xml(joint.main_beam.model))
    names = [element.tag.split("}")[-1] for element in root.iter()]
    assert names.count("FreeContour") == 2 and names.count("DualContour") == 2 and "Lap" not in names


def test_angled_tenon_too_short_for_the_obtuse_side_is_reported():
    _, _, _, _, errors = build(angle=70.0, length=15.0)  # the face lies further into the cross beam on the obtuse side

    assert errors
    assert "obtuse" in errors[-1].debug_info and "length" in errors[-1].debug_info


def test_angled_axis_below_the_cross_beams_face_is_reported():
    _, _, _, _, errors = build(angle=70.0, axis_offset=-20.0)  # the slanted end would swing into the cross beam

    assert errors
    assert "axis_offset" in errors[-1].debug_info


def test_angled_with_start_depth():
    _, joint, main, cross, errors = build(angle=70.0, start_depth=20.0, axis_offset=20.0)
    assert not errors

    assert [type(feature.contour_param_object) for feature in main.features] == [DualContour, DualContour]  # and the slab
    assert swings_out(joint, main, cross)


@pytest.mark.parametrize("profile, tool_angle", [(RotationalTenonProfile.PARALLEL, 15.0), (RotationalTenonProfile.CONICAL, 10.0)])
def test_angled_dovetail(profile, tool_angle):
    # with 15 degrees, a conical tenon, wide where it starts, would be out of the main beam before it reaches past the
    # face on the side of the obtuse angle
    _, joint, main, cross, errors = build(angle=70.0, end_mill=EndMillType.DOVETAIL, profile=profile, tool_angle=tool_angle)
    assert not errors
    assert Brep.from_box(cross.blank).volume - cross.geometry.volume == pytest.approx(tenon_volume(main, cross), rel=1e-3)

    assert swings_out(joint, main, cross, angles=(10.0, 30.0))
    away = -main.centerline.direction.unitized()  # pulled back along the main beam, by a third of the tenon
    pulled = main.geometry.transformed(Translation.from_vector(away * (joint.length / 3.0)))
    assert overlap(pulled, cross.geometry) > 1e-3 * tenon_volume(main, cross)  # locked along the main beam


def test_processing_joinery_again_replaces_the_features():
    model, joint, main, cross, _ = build()
    model.process_joinery()

    assert len(main.features) == 1 and len(cross.features) == 1


########################################################################
# Serialization
########################################################################


def test_json_roundtrip():
    model, joint, _, _, _ = build(
        profile=RotationalTenonProfile.CONICAL, end_mill=EndMillType.DOVETAIL, tool_angle=12.0, tenon_shape=TenonShapeType.RADIUS, axis_offset=15.0, tool_diameter=20.0
    )

    copy = json_loads(json_dumps(model))
    other = list(copy.joints)[0]
    assert isinstance(other, TRotationalTenonMortiseJoint)
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(joint, minimal=True))
    assert not copy.process_joinery()


def test_protobuf_roundtrip():
    import compas_timber.proto.conversions  # noqa: F401
    from compas_pb import pb_dump_bts
    from compas_pb import pb_load_bts

    _, joint, _, _, _ = build(profile=RotationalTenonProfile.CONICAL, end_mill=EndMillType.DOVETAIL, start_width=80.0, axis_offset=-20.0, tool_diameter=20.0)

    other = pb_load_bts(pb_dump_bts(joint))
    assert type(other) is TRotationalTenonMortiseJoint
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(joint, minimal=True))
