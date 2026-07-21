from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Frame
from compas_timber.elements import Beam
from compas_timber.connections import LButtJoint
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication.pocket import Pocket
from compas_timber.fabrication.lap import Lap
from compas_timber.model import TimberModel

import pytest
from compas.geometry import Plane
from compas.geometry import Translation
from compas.data import json_dumps, json_loads
from compas.tolerance import TOL


def test_L_butt_joint_create():
    beam_a = Beam(frame=Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]), width=100, height=200, length=100)
    beam_b = Beam(frame=Frame([0, 0, 0], [0, 1, 0], [1, 0, 0]), width=100, height=200, length=100)
    joint = LButtJoint(beam_a, beam_b, mill_depth=50, small_beam_butts=True, modify_cross=True)
    joint.add_features()
    assert isinstance(joint, LButtJoint)


@pytest.fixture
def cross_beam():
    cross_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=1.000, y=0.000, z=0.000), yaxis=Vector(x=0.000, y=1.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return cross_beam


@pytest.fixture
def planar_beam():
    planar_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=0.707, y=-0.000, z=0.707), yaxis=Vector(x=0.000, y=1.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return planar_beam


@pytest.fixture
def non_planar_beam():
    non_planar_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=0.632, y=0.447, z=0.632), yaxis=Vector(x=-0.577, y=1, z=0.000)),
        width=30.000,
        height=30.000,
        length=223.607,
    )
    return non_planar_beam


def test_L_butt_joint_features_planar_lap(cross_beam, planar_beam):
    joint = LButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=False, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Lap)


def test_L_butt_joint_features_non_planar_lap(cross_beam, non_planar_beam):
    joint = LButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=False, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Lap)


def test_L_butt_joint_features_planar_pocket(cross_beam, planar_beam):
    joint = LButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_planar_pocket_conical_tool(cross_beam, planar_beam):
    joint = LButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=True)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_non_planar_pocket(cross_beam, non_planar_beam):
    joint = LButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_non_planar_pocket_conical_tool(cross_beam, non_planar_beam):
    joint = LButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=True)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_small_beam_butts():
    big_beam = Beam(frame=Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]), width=100, height=200, length=100)
    small_beam = Beam(frame=Frame([0, 0, 0], [0, 1, 0], [1, 0, 0]), width=100, height=100, length=100)
    model = TimberModel()
    model.add_elements([big_beam, small_beam])
    joint = LButtJoint.create(model, big_beam, small_beam, mill_depth=50, small_beam_butts=False)
    joint_sbb = LButtJoint.create(model, big_beam, small_beam, mill_depth=50, small_beam_butts=True)

    assert big_beam == joint.main_beam, "small_beam_butts is False, Order stays the same"
    assert small_beam == joint.cross_beam, "small_beam_butts is False, Order stays the same"
    assert big_beam == joint_sbb.cross_beam, "small_beam_butts is True, Order changes"
    assert small_beam == joint_sbb.main_beam, "small_beam_butts is False, Order changes"


def test_L_butt_joint_butt_and_back_plane_creation(cross_beam, planar_beam):
    """Ensure butt_plane and back_plane passed to create() are stored and exposed."""
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    butt_plane = Plane(Point(0, 0, 0), Vector(0, 1, 0))
    # back_plane must be parallel to planar_beam's (main_beam's) centerline, i.e. its normal must be perpendicular
    # to planar_beam's xaxis (0.707, 0, 0.707)
    back_plane = Plane(Point(0, 0, 0), Vector(1, 0, -1))

    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(butt_plane))
    back_plane_id = planar_beam.add_user_ref_plane(Frame.from_plane(back_plane))

    joint = LButtJoint.create(
        model,
        main_beam=planar_beam,
        cross_beam=cross_beam,
        butt_plane_id=butt_plane_id,
        back_plane_id=back_plane_id,
    )

    assert joint.butt_plane is not None
    assert joint.back_plane is not None
    assert TOL.is_allclose(joint.butt_plane.normal, butt_plane.normal)
    assert TOL.is_allclose(joint.back_plane.normal, back_plane.normal)


def test_L_butt_joint_back_plane_survives_main_beam_extension(cross_beam, planar_beam):
    """A back_plane registered on main_beam before joining should still resolve to the same world-space
    plane even if main_beam's blank gets extended afterwards (e.g. by this or another joint's own
    add_extensions()), independently of back_plane_id.

    Unlike test_L_butt_joint_butt_and_back_plane_creation, this also checks the resolved plane's point,
    not just its normal - the normal is unaffected by the translation this bug introduces, so checking
    only the normal (as that test does) would not catch it.

    back_plane_id is resolved via main_beam.get_user_ref_plane(), which is relative to ref_frame.
    ref_frame is derived from main_beam's blank and shifts whenever the blank is extended (as joints
    routinely do), so a plane registered before joining drifts to the wrong world location afterwards.
    See test_user_ref_plane_survives_blank_extension in test_beam.py for the root cause.
    """
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    back_plane = Plane(Point(0, 0, 0), Vector(1, 0, -1))
    back_plane_id = planar_beam.add_user_ref_plane(Frame.from_plane(back_plane))

    joint = LButtJoint.create(
        model,
        main_beam=planar_beam,
        cross_beam=cross_beam,
        back_plane_id=back_plane_id,
    )

    # simulate a joint (this one or another) extending main_beam's blank before back_plane is resolved
    planar_beam.add_blank_extension(start=50.0, end=0.0, joint_key="fake_joint")

    assert TOL.is_allclose(joint.back_plane.point, back_plane.point)
    assert TOL.is_allclose(joint.back_plane.normal, back_plane.normal)


def test_L_butt_joint_copy_and_transform_preserve_planes(cross_beam, planar_beam):
    """Test that butt/back planes survive model serialization and model transforms."""
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    butt_plane = Plane(Point(0, 0, 0), Vector(0, 1, 0))
    # back_plane must be parallel to planar_beam's (main_beam's) centerline, i.e. its normal must be perpendicular
    # to planar_beam's xaxis (0.707, 0, 0.707)
    back_plane = Plane(Point(0, 0, 0), Vector(1, 0, -1))

    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(butt_plane))
    back_plane_id = planar_beam.add_user_ref_plane(Frame.from_plane(back_plane))

    joint = LButtJoint.create(
        model,
        main_beam=planar_beam,
        cross_beam=cross_beam,
        butt_plane_id=butt_plane_id,
        back_plane_id=back_plane_id,
    )

    # copy the model via JSON round-trip
    model_copy = json_loads(json_dumps(model))
    copied_joints = list(model_copy.joints)
    assert len(copied_joints) == 1
    copied_joint = copied_joints[0]

    assert copied_joint.butt_plane is not None
    assert copied_joint.back_plane is not None
    assert TOL.is_allclose(copied_joint.butt_plane.normal, butt_plane.normal)
    assert TOL.is_allclose(copied_joint.back_plane.normal, back_plane.normal)

    # transform the original model and ensure planes follow the transform
    translation = Translation.from_vector([10.0, 5.0, -2.0])
    # capture original plane points
    orig_butt_point = joint.butt_plane.point
    orig_back_point = joint.back_plane.point

    model.transform(translation)

    # after transform, the joint's planes points should have been transformed by same translation
    new_butt_point = joint.butt_plane.point
    new_back_point = joint.back_plane.point

    assert TOL.is_allclose([new_butt_point.x - orig_butt_point.x, new_butt_point.y - orig_butt_point.y, new_butt_point.z - orig_butt_point.z], [10.0, 5.0, -2.0])
    assert TOL.is_allclose([new_back_point.x - orig_back_point.x, new_back_point.y - orig_back_point.y, new_back_point.z - orig_back_point.z], [10.0, 5.0, -2.0])


def test_L_butt_joint_butt_plane_rejects_non_parallel_plane(cross_beam, planar_beam):
    """butt_plane's normal must be perpendicular to the cross beam's centerline (x-axis).

    Unlike `CutPlaneSpec`, `add_user_ref_plane` doesn't validate anything at registration time -
    any frame can be registered. The perpendicularity check now happens lazily, when the joint
    actually resolves `butt_plane_id` into a plane.
    """
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    # cross_beam's centerline runs along (1, 0, 0), so a plane with a normal that has a component
    # along that axis is not parallel to the centerline and should be rejected.
    invalid_butt_plane = Plane(Point(0, 0, 0), Vector(1, 1, 0))
    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(invalid_butt_plane))
    joint = LButtJoint(planar_beam, cross_beam, butt_plane_id=butt_plane_id)

    with pytest.raises(BeamJoiningError):
        joint.butt_plane


def test_L_butt_joint_back_plane_rejects_non_parallel_plane(cross_beam, planar_beam):
    """back_plane's normal must be perpendicular to the main beam's centerline (x-axis).

    Validated lazily on `back_plane` resolution, same as `butt_plane` above.
    """
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    # planar_beam's centerline runs along (0.707, 0, 0.707), which is not perpendicular to (0, 0, 1).
    invalid_back_plane = Plane(Point(0, 0, 0), Vector(0, 0, 1))
    back_plane_id = planar_beam.add_user_ref_plane(Frame.from_plane(invalid_back_plane))
    joint = LButtJoint(planar_beam, cross_beam, back_plane_id=back_plane_id)

    with pytest.raises(BeamJoiningError):
        joint.back_plane


def test_L_butt_joint_butt_plane_recess_without_mill_depth_adds_no_feature(cross_beam, planar_beam):
    """A butt_plane_id that recesses into the cross beam should NOT add any feature without an explicit mill_depth.

    There's no auto-detection of a recess from the plane's position - the caller must say how deep to mill.
    """
    default_joint = LButtJoint(planar_beam, cross_beam, modify_cross=False)
    ref_side = cross_beam.ref_sides[default_joint.cross_beam_ref_side_index]
    recessed_plane = Plane(ref_side.point - ref_side.normal * 8.0, ref_side.normal)
    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(recessed_plane))

    joint = LButtJoint(planar_beam, cross_beam, modify_cross=False, butt_plane_id=butt_plane_id)
    joint.add_features()

    assert len(cross_beam.features) == 0
    assert len(planar_beam.features) == 1


def test_L_butt_joint_butt_plane_flush_without_mill_depth_adds_no_feature(cross_beam, planar_beam):
    """A butt_plane_id flush with the cross beam's face and no mill_depth should not add any cross-beam feature."""
    default_joint = LButtJoint(planar_beam, cross_beam, modify_cross=False)
    ref_side = cross_beam.ref_sides[default_joint.cross_beam_ref_side_index]
    flush_plane = Plane(ref_side.point, ref_side.normal)
    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(flush_plane))

    joint = LButtJoint(planar_beam, cross_beam, modify_cross=False, butt_plane_id=butt_plane_id)
    joint.add_features()

    assert len(cross_beam.features) == 0
    assert len(planar_beam.features) == 1


def test_L_butt_joint_butt_plane_mill_depth_offsets_along_main_beam_centerline(cross_beam, planar_beam):
    """mill_depth should push the pocket's bottom past butt_plane, along the main beam's centerline direction."""
    default_joint = LButtJoint(planar_beam, cross_beam, modify_cross=False)
    ref_side = cross_beam.ref_sides[default_joint.cross_beam_ref_side_index]
    recessed_plane = Plane(ref_side.point - ref_side.normal * 8.0, ref_side.normal)
    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(recessed_plane))

    joint_shallow = LButtJoint(planar_beam, cross_beam, modify_cross=False, mill_depth=4.0, butt_plane_id=butt_plane_id)
    joint_deep = LButtJoint(planar_beam, cross_beam, modify_cross=False, mill_depth=8.0, butt_plane_id=butt_plane_id)

    # vertex 4 of the hexahedron is always a bottom_plane / side_a / end_a intersection (see polyhedron_from_box_planes)
    bottom_shallow = joint_shallow._get_milling_volume_for_pocket().vertices[4]
    bottom_deep = joint_deep._get_milling_volume_for_pocket().vertices[4]

    # the bottom face moved exactly by the mill_depth delta, parallel to the main beam's centerline
    assert TOL.is_close(bottom_shallow.distance_to_point(bottom_deep), 4.0)
    direction = Vector.from_start_end(bottom_shallow, bottom_deep).unitized()
    centerline_direction = planar_beam.centerline.direction.unitized()
    assert TOL.is_allclose(direction, centerline_direction) or TOL.is_allclose(direction, -centerline_direction)

    joint_deep.add_features()
    assert len(cross_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_butt_plane_zero_angle_pure_offset(cross_beam, planar_beam):
    """A butt_plane parallel to (but offset from) the default cross-beam side should round-trip exactly."""
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    default_ref_side = cross_beam.ref_sides[2]  # opposite side from the default, picked arbitrarily but parallel to centerline
    offset_plane = Plane(default_ref_side.point + default_ref_side.normal * 5.0, default_ref_side.normal)
    butt_plane_id = cross_beam.add_user_ref_plane(Frame.from_plane(offset_plane))

    joint = LButtJoint.create(model, main_beam=planar_beam, cross_beam=cross_beam, butt_plane_id=butt_plane_id)

    assert TOL.is_allclose(joint.butt_plane.normal, offset_plane.normal)
    assert TOL.is_allclose(joint.butt_plane.point, offset_plane.point)
