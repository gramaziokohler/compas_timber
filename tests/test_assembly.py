#import pytest
from compas.geometry import Frame, Point, Vector
from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
import copy


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


def test_deepcopy():
    A = TimberAssembly()
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, width = 0.1, height = 0.2, length = 1.0)
    B2 = Beam(F1, width = 0.2, height = 0.4, length = 1.0)
    A.add_beam(B1)
    A.add_beam(B2)

    Acopy = copy.deepcopy(A)
    #TODO: Frame throws an error when Frame is None
    #TODO: assembly KeyError


if __name__ == "__main__":
    test_create()
    test_add_beam()
    test_add_joint()
    test_remove_joint()
    test_deepcopy()
    print("\n *** all tests passed ***\n\n")

