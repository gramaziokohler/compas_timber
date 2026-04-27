from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Frame
from compas_timber.elements import Beam
from compas_timber.connections import LButtJoint
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
    back_plane = Plane(Point(0, 0, 0), Vector(0, 0, 1))

    joint = LButtJoint.create(model, main_beam=planar_beam, cross_beam=cross_beam, butt_plane=butt_plane, back_plane=back_plane)

    assert joint.butt_plane is not None
    assert joint.back_plane is not None
    assert TOL.is_allclose(joint.butt_plane.normal, butt_plane.normal)
    assert TOL.is_allclose(joint.back_plane.normal, back_plane.normal)


def test_L_butt_joint_copy_and_transform_preserve_planes(cross_beam, planar_beam):
    """Test that butt/back planes survive model serialization and model transforms."""
    model = TimberModel()
    model.add_elements([planar_beam, cross_beam])

    butt_plane = Plane(Point(0, 0, 0), Vector(0, 1, 0))
    back_plane = Plane(Point(0, 0, 0), Vector(0, 0, 1))

    joint = LButtJoint.create(model, main_beam=planar_beam, cross_beam=cross_beam, butt_plane=butt_plane, back_plane=back_plane)

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
