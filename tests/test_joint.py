from copy import deepcopy

from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.joint import Joint
from compas_timber.parts.beam import Beam


def test_create():

    # try create with beams
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()
    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A, [B1, B2])

    assert B1 in J.beams
    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.joints[0] == J


def test_remove_joint():
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()
    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A, [B1, B2])

    assert A.contains(J) == True

    A.remove_joint(J)

    assert len(list(A.graph.nodes())) == 2
    assert len(list(A.graph.edges())) == 0
    assert len(A.joints) == 0
    # assert J.parts == [] will not work if assembly==None
    assert J.assembly == None


def test_joint_override_protection():
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()
    B3 = Beam()
    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    J = Joint(A, [B1, B2])

    assert A.are_parts_joined([B1, B2]) == True
    assert A.are_parts_joined([B1, B3]) == False

    A.remove_joint(J)
    assert A.are_parts_joined([B1, B2]) == False


def test__eq__():

    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(2, 0, 0), Vector(0, 0, 1), 0.1, 0.2)
    B2 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1), 0.1, 0.2)
    B3 = Beam.from_endpoints(
        Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1), 0.1, 0.2
    )  # same as B2
    B4 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1), 0.1, 0.4)
    A = TimberAssembly()
    for b in [B1, B2, B3, B4]:
        A.add_beam(b)

    J1 = Joint(A, [B1, B2])
    # J2 = Joint([B1, B2], A) # this is failing because B1 and B2 are already joined
    # assert J1 == J2


def test_deepcopy():
    # TODO: not sure this make sense at all?
    # Normally you wouldn't deepcopy individual joints (duplicate protection in assembly),
    # but maybe it's needed for deepcopy of assembly?
    A = TimberAssembly()
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(2, 0, 0), Vector(0, 0, 1), 0.1, 0.2)
    B2 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1), 0.1, 0.2)
    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A, [B1, B2])
    J_copy = deepcopy(J)

    assert J_copy.beams[0] == J.beams[0]
    # assert J_copy.assembly == J.assembly #failing


if __name__ == "__main__":
    print("\n-------------------------------")
    test_create()
    test_remove_joint()
    test_joint_override_protection()
    test__eq__()
    test_deepcopy()
    print("\n *** all tests passed ***\n\n")
