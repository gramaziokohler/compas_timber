from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly import TimberAssembly
from compas_timber.connections import TButtJoint
from compas_timber.parts import Beam

geometry_type = "mesh"


def test_create():
    B1 = Beam.from_endpoints(
        Point(0, 0.5, 0),
        Point(1, 0.5, 0),
        z_vector=Vector(0, 0, 1),
        width=0.100,
        height=0.200,
        geometry_type=geometry_type,
    )
    B2 = Beam.from_endpoints(
        Point(0, 0.0, 0),
        Point(0, 1.0, 0),
        z_vector=Vector(0, 0, 1),
        width=0.100,
        height=0.200,
        geometry_type=geometry_type,
    )
    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    TButtJoint.create(A, B1, B2)
