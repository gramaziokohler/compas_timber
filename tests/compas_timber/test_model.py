from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import Wall
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


def test_create():
    model = TimberModel()
    assert model


def test_add_element():
    A = TimberModel()
    B = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    A.add_element(B)

    assert B in A.beams
    assert B in A.elements()
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert list(A.beams)[0] is B
    assert len(list(A.beams)) == 1


def test_add_joint():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(b1)
    model.add_element(b2)
    _ = LButtJoint.create(model, b1, b2)

    assert len(list(model.beams)) == 2
    assert len(list(model.joints)) == 1


def test_get_joint_from_interaction():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(b1)
    model.add_element(b2)
    joint = LButtJoint.create(model, b1, b2)

    assert joint is list(model.joints)[0]


def test_copy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert list(A_copy.beams)[0] is not list(A.beams)[0]


def test_deepcopy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert list(A_copy.beams)[0] is not list(A.beams)[0]


def test_beams_have_keys_after_serialization():
    A = TimberModel()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    A.add_element(B1)
    A.add_element(B2)
    A.add_element(B3)
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
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A = json_loads(json_dumps(A))


def test_serialization_with_t_butt_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    a = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    a.add_element(b1)
    a.add_element(b2)
    _ = TButtJoint.create(a, b1, b2)

    a = json_loads(json_dumps(a))

    assert len(list(a.joints)) == 1
    assert type(list(a.joints)[0]) is TButtJoint


def test_generator_properties():
    model = TimberModel()

    polyline = Polyline(
        [
            Point(x=0.0, y=184.318671947, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=4252.92700512),
        ]
    )

    plate = Plate.from_outline_thickness(polyline, 10.0, Vector(1, 0, 0))
    model.add_element(plate)

    beam = Beam(Frame.worldXY(), 10.0, 10.0, 10.0)
    model.add_element(beam)

    wall = Wall.from_boundary(polyline=Polyline([[100, 0, 0], [100, 100, 0], [200, 100, 0], [200, 0, 0], [100, 0, 0]]), normal=Vector.Zaxis(), thickness=10)
    model.add_element(wall)

    assert len(list(model.plates)) == 1
    assert len(list(model.beams)) == 1
    assert len(list(model.walls)) == 1


def test_type_properties():
    polyline = Polyline(
        [
            Point(x=0.0, y=184.318671947, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=4252.92700512),
        ]
    )

    plate = Plate.from_outline_thickness(polyline, 10.0, Vector(1, 0, 0))
    beam = Beam(Frame.worldXY(), 10.0, 10.0, 10.0)
    wall = Wall.from_boundary(polyline=Polyline([[100, 0, 0], [100, 100, 0], [200, 100, 0], [200, 0, 0], [100, 0, 0]]), normal=Vector.Zaxis(), thickness=10)

    assert plate.is_plate
    assert beam.is_beam
    assert wall.is_wall

    assert not plate.is_beam
    assert not plate.is_wall
    assert not beam.is_wall
    assert not beam.is_plate
    assert not wall.is_plate
    assert not wall.is_beam
