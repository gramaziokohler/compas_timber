from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.elements import PlateFastener
from compas_timber.elements import FastenerTimberInterface


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
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    I1 = FastenerTimberInterface()
    I2 = FastenerTimberInterface()
    F = PlateFastener(interfaces=[I1, I2])
    instance = TButtJoint.create(A, B1, B2, fastener=F)

    assert len(instance.elements) == 4
    assert isinstance(instance, TButtJoint)
    assert instance.main_beam == B1
    assert instance.cross_beam == B2
    assert len(list(A.interactions())) == 5
    assert len(list(A.copy().elements())) == 4


def test_create_t_butt_with_depth():
    beam_a = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    beam_b = Beam.from_endpoints(Point(0, 0.0, 0), Point(0, 1.0, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)

    butt = TButtJoint(beam_a, beam_b, mill_depth=0.1)

    butt.add_features()
