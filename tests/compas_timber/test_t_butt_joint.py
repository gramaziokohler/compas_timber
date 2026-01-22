import pytest

from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Frame

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.elements import PlateFastener
from compas_timber.elements import FastenerTimberInterface
from compas_timber.fabrication.pocket import Pocket
from compas_timber.fabrication.lap import Lap


def test_create():
    B1 = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    B2 = Beam.from_endpoints(Point(0, 0.0, 0), Point(0, 1.0, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    instance = TButtJoint.create(A, B1, B2)

    assert len(instance.elements) == 2
    assert isinstance(instance, TButtJoint)
    assert instance.main_beam == B1
    assert instance.cross_beam == B2


def test_create_with_fastener():
    B1 = Beam.from_endpoints(Point(0, 5, 0), Point(10, 5, 0), z_vector=Vector(0, 0, 1), width=1, height=2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(0, 10, 0), z_vector=Vector(0, 0, 1), width=1, height=2)
    model = TimberModel()
    model.add_element(B1)
    model.add_element(B2)
    I1 = FastenerTimberInterface()
    I2 = FastenerTimberInterface()
    F = PlateFastener(interfaces=[I1, I2])
    instance = TButtJoint.create(model, B1, B2, fastener=F)

    assert len(instance.elements) == 4
    assert isinstance(instance, TButtJoint)
    assert instance.main_beam == B1
    assert instance.cross_beam == B2
    assert len(list(model.joints)) == 1  # The model should contain one joint -> the TButtJoint w/ fastener(s)
    assert len(list(model._graph.edges())) == 5  # The model should contain 5 edges -> 1 joint + 4 interactions between the two beams and the two plate fasteners
    assert len(list(model.elements())) == 4  # The model should contain 4 elements -> 2 beams + 2 plate fasteners


def test_create_t_butt_with_depth():
    beam_a = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    beam_b = Beam.from_endpoints(Point(0, 0.0, 0), Point(0, 1.0, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    butt = TButtJoint(beam_a, beam_b, mill_depth=0.1)
    butt.add_features()


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
        frame=Frame(point=Point(x=100.0, y=0.000, z=0.000), xaxis=Vector(x=0.707, y=-0.000, z=0.707), yaxis=Vector(x=0.000, y=1.000, z=0.000)),
        width=30.000,
        height=30.000,
        length=200.000,
    )
    return planar_beam


@pytest.fixture
def non_planar_beam():
    non_planar_beam = Beam(
        frame=Frame(point=Point(x=100.000, y=0.000, z=0.000), xaxis=Vector(x=0.655, y=0.378, z=0.655), yaxis=Vector(x=-0.500, y=0.866, z=0.000)),
        width=30.000,
        height=30.000,
        length=223.607,
    )
    return non_planar_beam


def test_L_butt_joint_features_planar_lap(cross_beam, planar_beam):
    joint = TButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=False, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Lap)


def test_L_butt_joint_features_non_planar_lap(cross_beam, non_planar_beam):
    joint = TButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=False, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Lap)


def test_L_butt_joint_features_planar_pocket(cross_beam, planar_beam):
    joint = TButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_planar_pocket_conical_tool(cross_beam, planar_beam):
    joint = TButtJoint(planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=True)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_non_planar_pocket(cross_beam, non_planar_beam):
    joint = TButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=False)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)


def test_L_butt_joint_features_non_planar_pocket_conical_tool(cross_beam, non_planar_beam):
    joint = TButtJoint(non_planar_beam, cross_beam, mill_depth=10, modify_cross=False, force_pocket=True, conical_tool=True)
    joint.add_features()
    assert len(cross_beam.features) == 1
    assert len(non_planar_beam.features) == 1
    assert isinstance(cross_beam.features[0], Pocket)
