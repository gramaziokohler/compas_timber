"""Placement of elements nested in the model tree: transforming an ancestor, (de)serialization, and joint re-processing."""

import math

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Reflection
from compas.geometry import Rotation
from compas.geometry import Scale
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import distance_point_plane
from compas.tolerance import TOL
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.connections import CutPlaneSpec
from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections.joint import location_from_centerlines
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel

T = Translation.from_vector([500, -300, 1000]) * Rotation.from_axis_and_angle([0, 0, 1], math.radians(35))


def assert_same_frame(a, b):
    assert TOL.is_allclose(a.point, b.point)
    assert TOL.is_allclose(a.xaxis, b.xaxis)
    assert TOL.is_allclose(a.yaxis, b.yaxis)


def assert_same_plane(a, b):
    assert TOL.is_zero(distance_point_plane(a.point, b))
    assert TOL.is_allclose(a.normal.unitized(), b.normal.unitized())


@pytest.fixture
def parent_model():
    model = TimberModel()
    outline = Polyline([Point(1000, 0, 0), Point(4000, 0, 0), Point(4000, 2400, 0), Point(1000, 2400, 0), Point(1000, 0, 0)])
    parent = Plate.from_outline_thickness(outline, 200)
    model.add_element(parent)
    # beams are placed in the parent's local coordinates
    beam_a = Beam.from_centerline(Line(Point(0, 0, 0), Point(1200, 0, 0)), 80, 160)
    beam_b = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 1200, 0)), 80, 160)
    model.add_element(beam_a, parent=parent)
    model.add_element(beam_b, parent=parent)
    return model, parent, beam_a, beam_b


# ==========================================================================
# transforming an ancestor
# ==========================================================================


def test_child_beam_follows_transformed_parent(parent_model):
    _, parent, beam_a, _ = parent_model
    frame_before = beam_a.frame  # populates the cache
    centerline_before = beam_a.centerline

    parent.transform(T)

    assert_same_frame(beam_a.frame, frame_before.transformed(T))
    assert TOL.is_allclose(beam_a.centerline.start, centerline_before.start.transformed(T))


def test_setting_parent_transformation_updates_children(parent_model):
    _, parent, beam_a, _ = parent_model
    frame_before = beam_a.frame

    parent.transformation = T * parent.transformation

    assert_same_frame(beam_a.frame, frame_before.transformed(T))


def test_adding_element_under_parent_updates_cached_frame(parent_model):
    model, parent, _, _ = parent_model
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(500, 0, 0)), 80, 160)
    local_frame = beam.frame  # populates the cache while standalone

    model.add_element(beam, parent=parent)

    assert_same_frame(beam.frame, local_frame.transformed(parent.modeltransformation))


# ==========================================================================
# (de)serialization after a transformation
# ==========================================================================


def test_transformed_parent_survives_serialization(parent_model):
    model, parent, beam_a, _ = parent_model
    parent.transform(T)
    expected_outline = parent.outline_a
    expected_beam_frame = beam_a.frame

    model_copy = json_loads(json_dumps(model))
    parent_copy = model_copy.plates[0]
    beam_copy = next(e for e in parent_copy.children if isinstance(e, Beam) and TOL.is_allclose(e.frame.point, beam_a.frame.point))

    assert TOL.is_allclose(parent_copy.outline_a.points[1], expected_outline.points[1])
    assert_same_frame(beam_copy.frame, expected_beam_frame)


def test_transformed_plate_survives_serialization():
    plate = Plate(frame=Frame([100, 0, 0], [1, 0, 0], [0, 1, 0]), length=1000, width=500, thickness=20)
    plate.transform(T)
    expected = plate.frame

    plate_copy = json_loads(json_dumps(plate))

    assert_same_frame(plate_copy.frame, expected)


def json_roundtrip(model):
    return json_loads(json_dumps(model))


def protobuf_roundtrip(model):
    import compas_timber.proto.conversions  # noqa: F401

    return pb_load_bts(pb_dump_bts(model))


@pytest.mark.parametrize("roundtrip", [json_roundtrip, protobuf_roundtrip], ids=["json", "protobuf"])
def test_transformed_hierarchy_survives_serialization(roundtrip):
    """Every element of a moved tree loads back where it was, including children with their own placement."""
    model = TimberModel()
    outline = Polyline([Point(1000, 0, 0), Point(4000, 0, 0), Point(4000, 2400, 0), Point(1000, 2400, 0), Point(1000, 0, 0)])
    parent = Plate.from_outline_thickness(outline, 200)
    model.add_element(parent)
    # children placed in the parent's local coordinates, rotated relative to it
    plate = Plate(Frame([300, 400, 200], [0, 1, 0], [-1, 0, 0]), 600, 300, 20)
    nested_plate = Plate(Frame([1500, 200, 200], [1, 1, 0], [-1, 1, 0]), 800, 600, 50)
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1200, 0, 0)), 80, 160)
    for child in (plate, nested_plate, beam):
        model.add_element(child, parent=parent)
    plate.transform(Translation.from_vector([100, 50, 0]))  # moved on its own, then with its parent
    parent.transform(T)

    def placement(element):
        outline = list(element.outline_a.points) if hasattr(element, "outline_a") else []
        return [element.frame.point, element.frame.xaxis, element.frame.yaxis] + outline

    expected = {str(e.guid): placement(e) for e in model.elements()}
    assert len(expected) == 4  # parent, plate, nested plate, beam

    model_copy = roundtrip(model)

    for element in model_copy.elements():
        for actual, wanted in zip(placement(element), expected.pop(str(element.guid))):
            assert TOL.is_allclose(actual, wanted), type(element).__name__
    assert not expected


@pytest.mark.parametrize("transformation", [Scale.from_factors([2, 2, 2]), Reflection.from_frame(Frame.worldYZ())], ids=["scale", "mirror"])
def test_plate_rejects_non_rigid_transformations(transformation):
    element = Plate(Frame.worldXY(), 100, 100, 10)
    with pytest.raises(ValueError):
        element.transform(transformation)


# ==========================================================================
# joints after their elements moved
# ==========================================================================


def test_l_miter_reprocessed_after_parent_moved(parent_model):
    model, parent, beam_a, beam_b = parent_model
    joint = LMiterJoint.create(model, beam_a, beam_b)
    model.process_joinery()
    planes_before = joint.cutting_planes

    parent.transform(T)
    model.process_joinery()

    for plane, plane_before in zip(joint.cutting_planes, planes_before):
        assert_same_plane(plane, plane_before.transformed(T))


@pytest.mark.requires_occ  # the lap's features are applied as Breps
def test_lap_joint_reprocessed_after_model_moved():
    model = TimberModel()
    beam_a = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 80, 160)
    beam_b = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 1000, 0)), 80, 160)
    model.add_elements([beam_a, beam_b])
    joint = LLapJoint.create(model, beam_a, beam_b)
    model.process_joinery()
    plane_before = joint.cutting_plane_a

    model.transform(T)
    model.process_joinery()

    assert_same_plane(joint.cutting_plane_a, plane_before.transformed(T))


def test_explicit_joint_location_follows_elements(parent_model):
    model, parent, beam_a, beam_b = parent_model
    location = Point(10, 20, 30).transformed(parent.modeltransformation)
    joint = LMiterJoint.create(model, beam_a, beam_b, location=location)

    parent.transform(T)
    assert TOL.is_allclose(joint.location, location.transformed(T))


def test_explicit_joint_location_follows_elements_after_reload(parent_model):
    model, parent, beam_a, beam_b = parent_model
    location = Point(10, 20, 30).transformed(parent.modeltransformation)
    LMiterJoint.create(model, beam_a, beam_b, location=location)

    model_copy = json_loads(json_dumps(model))
    model_copy.plates[0].transform(T)  # before the location is first read

    assert TOL.is_allclose(next(iter(model_copy.joints)).location, location.transformed(T))


def test_derived_joint_location_stays_derived_after_reload():
    model = TimberModel()
    beam_a = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 80, 160)
    beam_b = Beam.from_centerline(Line(Point(1000, 0, 0), Point(1000, 1000, 0)), 80, 160)
    model.add_elements([beam_a, beam_b])
    LButtJoint.create(model, beam_b, beam_a)

    joint_copy = next(iter(json_loads(json_dumps(model)).joints))
    location_before = joint_copy.location
    joint_copy.element_b.transform(Translation.from_vector([-300, 0, 0]))

    assert not TOL.is_allclose(joint_copy.location, location_before)
    assert TOL.is_allclose(joint_copy.location, location_from_centerlines(joint_copy.elements))


def test_custom_cut_planes_under_transformed_and_reloaded_parent(parent_model):
    model, parent, beam_a, beam_b = parent_model
    beam_c = Beam.from_centerline(Line(Point(1800, 0, 0), Point(3000, 0, 0)), 80, 160)
    beam_d = Beam.from_centerline(Line(Point(1800, 0, 0), Point(1800, 1200, 0)), 80, 160)
    model.add_element(beam_c, parent=parent)
    model.add_element(beam_d, parent=parent)
    miter = Plane(Point(0, 0, 0), Vector(1, -1, 0.3)).transformed(parent.modeltransformation)
    butt = Plane(Point(1840, 0, 0), Vector(-1, 0, -0.5)).transformed(parent.modeltransformation)
    LMiterJoint.create(model, beam_a, beam_b, miter_plane=CutPlaneSpec.from_plane(beam_a, miter))
    LButtJoint.create(model, beam_c, beam_d, butt_plane_spec=CutPlaneSpec.from_butt_plane(beam_c, beam_d, butt))
    model.process_joinery()

    parent.transform(T)
    model_copy = json_loads(json_dumps(model))
    model_copy.process_joinery()

    miter_joint = next(j for j in model_copy.joints if isinstance(j, LMiterJoint))
    butt_joint = next(j for j in model_copy.joints if isinstance(j, LButtJoint))
    assert_same_plane(miter_joint.miter_plane, miter.transformed(T))
    assert_same_plane(butt_joint.butt_plane, butt.transformed(T))


def test_model_transform_moves_parent_children(parent_model):
    model, parent, beam_a, beam_b = parent_model
    elements = [parent, beam_a, beam_b]
    before = [element.frame.point for element in elements]

    model.transform(Translation.from_vector([0, 0, 250]))

    for element, point in zip(elements, before):
        assert TOL.is_allclose(element.frame.point, point + Vector(0, 0, 250))
