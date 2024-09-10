from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def test_create():
    B1 = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    B2 = Beam.from_endpoints(Point(0, 0.0, 0), Point(0, 1.0, 0), z_vector=Vector(0, 0, 1), width=0.100, height=0.200)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    instance = TButtJoint.create(A, B1, B2)

    assert len(instance.beams) == 2
    assert isinstance(instance, TButtJoint)
    assert instance.main_beam == B1
    assert instance.cross_beam == B2
