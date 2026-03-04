from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Frame
from compas_timber.elements import Beam
from compas_timber.connections import LButtJoint
from compas_timber.fabrication.pocket import Pocket
from compas_timber.fabrication.lap import Lap

import pytest


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
