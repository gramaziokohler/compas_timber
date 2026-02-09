from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Frame
from compas.geometry import Plane
from compas_timber.elements import Beam
from compas_timber.connections import LMiterJoint
from compas_timber.model import TimberModel
from compas.tolerance import TOL

from compas.data import json_dumps
from compas.data import json_loads


import pytest


def test_L_butt_joint_create():
    beam_a = Beam(frame=Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]), width=100, height=200, length=100)
    beam_b = Beam(frame=Frame([0, 0, 0], [0, 1, 0], [1, 0, 0]), width=100, height=200, length=100)
    joint = LMiterJoint(beam_a, beam_b)
    joint.add_features()
    assert isinstance(joint, LMiterJoint)


@pytest.fixture
def beam_a():
    beam_a = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=1.000, y=0.000, z=0.000), yaxis=Vector(x=0.000, y=1.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return beam_a


@pytest.fixture
def beam_a_big():
    beam_a_big = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=1.000, y=0.000, z=0.000), yaxis=Vector(x=0.000, y=1.000, z=0.000)),
        width=80.000,
        height=30.000,
        length=200.000,
    )
    return beam_a_big


@pytest.fixture
def perp_beam():
    perp_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=0.000, y=1.000, z=0.000), yaxis=Vector(x=-1.000, y=0.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return perp_beam


@pytest.fixture
def non_planar_beam():
    non_planar_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=0.000, y=1.000, z=0.000), yaxis=Vector(x=-1.000, y=0.000, z=1.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return non_planar_beam


@pytest.fixture
def angle_beam():
    angle_beam = Beam(
        frame=Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=-1.000, y=1.000, z=0.000), yaxis=Vector(x=-1.000, y=-1.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200,
    )
    return angle_beam


def test_L_miter_joint_bisector_extensions(beam_a, perp_beam):
    joint = LMiterJoint(beam_a, perp_beam)
    joint.add_extensions()
    assert TOL.is_close(beam_a.blank_length, 215)
    assert TOL.is_close(perp_beam.blank_length, 215)


def test_L_miter_joint_bisector_extensions_big(beam_a_big, perp_beam):
    joint = LMiterJoint(beam_a_big, perp_beam)
    joint.add_extensions()
    # bisector miter at 90deg should extend each beam by half its width
    assert TOL.is_close(beam_a_big.blank_length, 240)
    assert TOL.is_close(perp_beam.blank_length, 215)


def test_L_miter_joint_ref_plane_extensions_big(beam_a_big, perp_beam):
    joint = LMiterJoint(beam_a_big, perp_beam, ref_side_miter=True)
    joint.add_extensions()
    # bisector miter at 90deg should extend each beam by half of the other beam's width
    assert joint.ref_side_miter
    assert TOL.is_close(beam_a_big.blank_length, 215)
    assert TOL.is_close(perp_beam.blank_length, 240)


def test_l_miter_user_defined_plane_extend_angle_beam(beam_a, angle_beam):
    joint = LMiterJoint(beam_a, angle_beam, miter_plane=Plane([0, 0, 0], [1, 0, 0]))
    joint.add_extensions()
    assert not joint.ref_side_miter 
    assert TOL.is_close(beam_a.blank_length, 200)
    assert TOL.is_close(angle_beam.blank_length, 215)


def test_l_miter_user_defined_plane_extend_beam_a(beam_a, angle_beam):
    joint = LMiterJoint(beam_a, angle_beam, miter_plane=Plane([0, 0, 0], [1, -1, 0]))
    joint.add_extensions()
    assert not joint.ref_side_miter 
    assert TOL.is_close(beam_a.blank_length, 215)
    assert TOL.is_close(angle_beam.blank_length, 200)


def test_L_miter_joint_bisector_features(beam_a, perp_beam):
    joint = LMiterJoint(beam_a, perp_beam)
    joint.add_extensions()
    joint.add_features()
    assert len(beam_a.features) == 1
    assert len(perp_beam.features) == 1


def test_L_miter_joint_bisector_features_clean(beam_a, perp_beam):
    joint = LMiterJoint(beam_a, perp_beam, clean=True)
    joint.add_extensions()
    joint.add_features()
    # since beams are coplanar, there should only be one cleaning cut per beam, 2 features per beam including miter cut
    assert len(beam_a.features) == 2
    assert len(perp_beam.features) == 2


def test_L_miter_joint_bisector_features_cutoff(beam_a, perp_beam):
    joint = LMiterJoint(beam_a, perp_beam, cutoff=True)
    joint.add_extensions()
    joint.add_features()
    # since beams are coplanar, there should only be one cleaning cut per beam, 2 features per beam including miter cut
    assert len(beam_a.features) == 2
    assert len(perp_beam.features) == 2


def test_L_miter_joint_bisector_features_clean_non_planar(beam_a, non_planar_beam):
    joint = LMiterJoint(beam_a, non_planar_beam, clean=True)
    joint.add_extensions()
    joint.add_features()
    # beam_a gets 2 cleaning cuts from non_planar_beam. non_planar_beam only gets one cleaning cut from beam_a
    assert len(beam_a.features) == 3
    assert len(non_planar_beam.features) == 2


def test_l_miter_joint_serialization(beam_a, perp_beam):
    model = TimberModel()
    model.add_elements([beam_a, perp_beam])
    joint = LMiterJoint.create(model, beam_a, perp_beam, ref_side_miter=True, clean=True)
    assert list(model.joints)[0] == joint
    model_copy = json_loads(json_dumps(model))
    assert len(list(model_copy.joints)) == 1
    joint_copy = list(model_copy.joints)[0]
    beam_a_copy = joint_copy.beam_a
    perp_beam_copy = joint_copy.beam_b
    assert joint.beam_a.guid == joint_copy.beam_a.guid
    assert joint.beam_b.guid == joint_copy.beam_b.guid
    assert joint.ref_side_miter
    assert joint.ref_side_miter == joint_copy.ref_side_miter
    assert joint.clean and joint_copy.clean
    assert len(beam_a_copy.features) == 0
    assert len(perp_beam_copy.features) == 0

    model_copy.process_joinery()
    assert len(beam_a_copy.features) == 2
    assert len(perp_beam_copy.features) == 2


def test_l_miter_joint_serialization_user_plane(beam_a, angle_beam):
    model = TimberModel()
    model.add_elements([beam_a, angle_beam])
    _ = LMiterJoint.create(model, beam_a, angle_beam, miter_plane=Plane([0, 0, 0], [1, 0, 0]))
    model_copy = json_loads(json_dumps(model))
    joint_copy = list(model_copy.joints)[0]
    assert joint_copy.miter_plane == Plane([0, 0, 0], [1, 0, 0])
