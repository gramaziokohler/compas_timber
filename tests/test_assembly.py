import pytest
from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint


def test_create():
    _ = TimberAssembly()


def test_add_beam():
    A = TimberAssembly()
    B = Beam()
    A.add_beam(B)

    assert B.key in A.beam_keys
    assert B in A.beams
    assert B.assembly is A
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert A.beams[0] == B
    assert len(A.beams) == 1


def test_add_joint():
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()

    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint([B1, B2], A)

    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.beams[0] == B1
    assert len(A.joints) == 1

def test_remove_joint():
    A = TimberAssembly()
    B1 = Beam()
    B2 = Beam()

    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint([B1, B2], A)

    A.remove_joint(J)
    assert len(list(A.graph.nodes())) == 2
    assert len(list(A.graph.edges())) == 0
    assert len(A.joints) == 0


if __name__ == "__main__":
    test_create()
    test_add_beam()
    test_add_joint()
    test_remove_joint()
    print("\n *** all tests passed ***\n\n")
