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
    assert B.assembly == A
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert A.beams[0] == B


if __name__ == "__main__":
    test_create()
    test_add_beam()
    print("\n *** all tests passed ***\n\n")
