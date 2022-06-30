import copy
import os
import pickle

import compas
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.joint import Joint
from compas_timber.parts.beam import Beam


def test_compas_json():
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), width=0.1, height=0.2, length=1.0)
    B2 = Beam(Frame.worldXY(), width=0.2, height=0.4, length=2.0)

    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A, [B1, B2])

    # TODO: this fails, circular reference -> happens already when adding a beam to assembly
    cwd = os.getcwd()
    filepath = os.path.join(cwd, r"\temp\test_assembly.json")
    compas.json_dump(A.data, filepath)


def test_pickle():
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), width=0.1, height=0.2, length=1.0)
    B2 = Beam(Frame.worldXY(), width=0.2, height=0.4, length=2.0)

    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A, [B1, B2])

    cwd = os.getcwd()
    filepath = os.path.join(cwd, r"\temp\test_assembly.pickle")
    with open(filepath, "wb") as f:
        pickle.dump(A, f)

    with open(filepath, "rb") as f:
        A_restored = pickle.load(f)

    assert isinstance(A_restored, TimberAssembly)
    assert A.parts()[0] == A_restored.parts()[0]
    assert A.graph.node == A_restored.graph.node
    assert A.joints[0] == A_restored.joints[0]


if __name__ == "__main__":
    test_pickle()
    test_compas_json()
    print("\n *** all tests passed ***\n\n")
