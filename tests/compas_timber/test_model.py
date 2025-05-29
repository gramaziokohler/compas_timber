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


def test_copy_model_with_processing_jackraftercut_proxy():
    from compas_timber.fabrication import JackRafterCutProxy
    from compas_timber.fabrication import JackRafterCut

    # Create a TimberModel instance
    model = TimberModel()

    # Add a beam to the model
    height, width, length = 200.11, 100.05, 2001.12
    frame = Frame(point=Point(x=390.000, y=780.000, z=0.000), xaxis=Vector(x=0.989, y=0.145, z=0.000), yaxis=Vector(x=-0.145, y=0.989, z=-0.000))
    beam = Beam(frame, length=length, width=width, height=height)
    model.add_element(beam)

    cutting_plane = Frame(point=Point(x=627.517, y=490.000, z=-187.681), xaxis=Vector(x=0.643, y=0.000, z=0.766), yaxis=Vector(x=0.000, y=1.000, z=-0.000))

    # Create a processing proxy for the model
    beam.add_feature(JackRafterCutProxy.from_plane_and_beam(cutting_plane, beam))

    copied_model = model.copy()

    copied_beams = list(copied_model.beams)
    assert len(copied_beams) == 1
    assert len(copied_beams[0].features) == 1
    assert isinstance(copied_beams[0].features[0], JackRafterCut)


def test_error_deepcopy_feature():
    from copy import deepcopy
    from compas_timber.errors import FeatureApplicationError

    error = FeatureApplicationError("mama", "papa", "dog")

    error = deepcopy(error)

    assert error.feature_geometry == "mama"
    assert error.element_geometry == "papa"
    assert error.message == "dog"


def test_error_deepcopy_fastener():
    from copy import deepcopy
    from compas_timber.errors import FastenerApplicationError

    error = FastenerApplicationError("mama", "papa", "dog")

    error = deepcopy(error)

    assert error.elements == "mama"
    assert error.fastener == "papa"
    assert error.message == "dog"


def test_error_deepcopy_joint():
    from copy import deepcopy
    from compas_timber.errors import BeamJoiningError

    error = BeamJoiningError("mama", "papa", "dog", "cucumber")

    error = deepcopy(error)

    assert error.beams == "mama"
    assert error.joint == "papa"
    assert error.debug_info == "dog"
    assert error.debug_geometries == "cucumber"
