import pytest_mock
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_timber.elements import Beam
from compas_timber.connections import Joint
from compas_timber.model import TimberModel
from compas_timber.structural import StructuralElementSolver


def test_add_joint_structural_segments_crossing_beams(mocker: pytest_mock.MockerFixture):
    f1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    beam1 = Beam(f1, length=1000, width=100, height=100)

    f2 = Frame(Point(0, 0, 200), Vector(0, 1, 0), Vector(0, 0, 1))
    beam2 = Beam(f2, length=1000, width=100, height=100)

    model = mocker.MagicMock(spec=TimberModel)

    joint = mocker.MagicMock(spec=Joint)
    joint.elements = [beam1, beam2]

    solver = StructuralElementSolver()
    solver.add_joint_structural_segments(joint, model)

    model.add_interaction_structural_segments.assert_called_once()

    args = model.add_interaction_structural_segments.call_args
    assert args[0][0] == beam1
    assert args[0][1] == beam2

    segments = args[0][2]
    assert len(segments) == 1
    segment = segments[0]

    p1 = segment.segment.start
    p2 = segment.segment.end

    assert (TOL.is_zero(p1.distance_to_point(Point(0, 0, 0))) and TOL.is_zero(p2.distance_to_point(Point(0, 0, 200)))) or (
        TOL.is_zero(p1.distance_to_point(Point(0, 0, 200))) and TOL.is_zero(p2.distance_to_point(Point(0, 0, 0)))
    )


def test_add_joint_structural_segments_intersecting_beams(mocker: pytest_mock.MockerFixture):
    f1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    beam1 = Beam(f1, length=1000, width=100, height=100)

    f2 = Frame(Point(0, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1))
    beam2 = Beam(f2, length=1000, width=100, height=100)

    model = mocker.MagicMock(spec=TimberModel)

    joint = mocker.MagicMock(spec=Joint)
    joint.elements = [beam1, beam2]

    solver = StructuralElementSolver()
    solver.add_joint_structural_segments(joint, model)

    model.add_interaction_structural_segments.assert_not_called()


def test_add_joint_structural_segments_multi_beam(mocker: pytest_mock.MockerFixture):
    f1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    beam1 = Beam(f1, length=1000, width=100, height=100)

    f2 = Frame(Point(0, 0, 200), Vector(0, 1, 0), Vector(0, 0, 1))
    beam2 = Beam(f2, length=1000, width=100, height=100)

    f3 = Frame(Point(0, 0, -200), Vector(0, 1, 0), Vector(0, 0, 1))
    beam3 = Beam(f3, length=1000, width=100, height=100)

    model = mocker.MagicMock(spec=TimberModel)

    joint = mocker.MagicMock(spec=Joint)
    joint.elements = [beam1, beam2, beam3]

    solver = StructuralElementSolver()
    solver.add_joint_structural_segments(joint, model)

    assert model.add_interaction_structural_segments.call_count >= 2

    calls = model.add_interaction_structural_segments.call_args_list
    pairs = []
    for call in calls:
        args = call[0]
        pairs.append({id(args[0]), id(args[1])})

    assert {id(beam1), id(beam2)} in pairs
    assert {id(beam1), id(beam3)} in pairs
