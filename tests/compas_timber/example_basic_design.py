from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.parts.beam import Beam


def create_beam():
    B = Beam.from_endpoints(
        Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200
    )
    print(B)
    pass


def create_assembly():
    A = TimberAssembly()
    print(A)
    pass


def mini_design():
    B1 = Beam.from_endpoints(
        Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200
    )
    B2 = Beam.from_endpoints(
        Point(0, 0.5, 0), Point(1, 0.5, 0), Vector(0, 0, 1), 0.100, 0.200
    )

    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    print(A._beams)

    J = TButtJoint(B2, B1)

    A.add_joint(J)
    A.connect([B1, B2], J)
    print(A)
    print(A._connections)


if __name__ == "__main__":
    mini_design()
