import pytest
from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint


def test_create():

    # try create empty
    _ = Joint()

    # try create with beams
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()
    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint([B1, B2], A)

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
    J = Joint([B1, B2], A)

    assert J.is_in_assembly(A) == True

    # A.remove_joint(J)
    J.remove_from_assembly()

    assert len(list(A.graph.nodes())) == 2
    assert len(list(A.graph.edges())) == 0
    assert len(A.joints) == 0
    assert J.parts == []
    assert J.assembly == None
    assert J.is_in_assembly(A) == False


def test_joint_override_protection():
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()
    B3 = Beam()
    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    J = Joint([B1, B2], A)

    assert A.are_parts_joined_already([b.key for b in [B1, B2]]) == True
    assert A.are_parts_joined_already([b.key for b in [B1, B3]]) == False

    J.remove_from_assembly()
    assert A.are_parts_joined_already([b.key for b in [B1, B2]]) == False


if __name__ == "__main__":
    print("\n-------------------------------")
    test_create()
    test_remove_joint()
    test_joint_override_protection()
    print("\n *** all tests passed ***\n\n")
