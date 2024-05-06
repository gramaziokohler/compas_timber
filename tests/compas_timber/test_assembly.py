from compas.data import json_dumps, json_loads
from compas.geometry import Frame, Point, Vector
from compas_timber.assembly import TimberModel
from compas_timber.connections import LButtJoint, TButtJoint
from compas_timber.parts import Beam


def test_create():
    model = TimberModel()
    assert model


def test_add_beam():
    A = TimberModel()
    B = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    A.add_beam(B)

    assert B in A.beams
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert A.beams[0] is B
    assert len(A.beams) == 1


def test_add_joint():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_beam(b1)
    model.add_beam(b2)
    _ = LButtJoint.create(model, b1, b2)

    assert len(model.beams) == 2
    assert len(model.joints) == 1


def test_copy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_beam(B1)
    A.add_beam(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert A_copy.beams[0] is not A.beams[0]


def test_deepcopy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_beam(B1)
    A.add_beam(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert A_copy.beams[0] is not A.beams[0]


def test_beams_have_keys_after_serialization():
    A = TimberModel()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    keys = [beam.guid for beam in A.beams]

    A = json_loads(json_dumps(A))

    assert keys == [beam.guid for beam in A.beams]


def test_serialization_with_l_butt_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_beam(B1)
    A.add_beam(B2)
    _ = LButtJoint.create(A, B1, B2)

    A = json_loads(json_dumps(A))


def test_serialization_with_t_butt_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    a = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    a.add_beam(b1)
    a.add_beam(b2)
    _ = TButtJoint.create(a, b1, b2)

    a = json_loads(json_dumps(a))

    assert len(a.joints) == 1
    assert type(a.joints[0]) is TButtJoint
