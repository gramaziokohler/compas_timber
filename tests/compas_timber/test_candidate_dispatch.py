import pytest
from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import get_connection_candidate
from compas_timber.connections.candidate_dispatch import find_connection_solver
from compas_timber.connections.candidate_dispatch import solve_topology
from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.elements import Plate


@pytest.fixture
def beam():
    return Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), 0.1, 0.1)


@pytest.fixture
def plate():
    outline = Polyline([Point(0, 0, 0), Point(0, 1, 0), Point(1, 1, 0), Point(1, 0, 0), Point(0, 0, 0)])
    return Plate.from_outline_thickness(outline, 0.1)


@pytest.fixture
def panel():
    outline = Polyline([Point(0, 0, 0), Point(0, 1, 0), Point(1, 1, 0), Point(1, 0, 0), Point(0, 0, 0)])
    return Panel.from_outline_thickness(outline, 0.1)


def test_find_connection_solver_beam_beam(beam):
    assert type(find_connection_solver(beam, beam)) is ConnectionSolver


def test_find_connection_solver_plate_plate(plate):
    assert type(find_connection_solver(plate, plate)) is PlateConnectionSolver


def test_find_connection_solver_panel_panel(panel):
    assert type(find_connection_solver(panel, panel)) is PlateConnectionSolver


def test_find_connection_solver_unsupported_pair_returns_none(beam, plate):
    assert find_connection_solver(beam, plate) is None


def test_solve_topology_unsupported_pair_returns_none(beam, plate):
    assert solve_topology(beam, plate) is None


def test_get_connection_candidate_unsupported_pair_returns_none_without_solving(beam, plate):
    """An unregistered type combination should short-circuit to None without invoking any solver."""
    assert get_connection_candidate(beam, plate, max_distance=1.0) is None


def test_get_connection_candidate_beams_ordered_main_first():
    cross = Beam.from_endpoints(Point(0, -1, 0), Point(0, 1, 0), 0.1, 0.1)
    main = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), 0.1, 0.1)
    candidate = get_connection_candidate(cross, main, max_distance=None)
    assert type(candidate) is JointCandidate
    assert candidate.topology == JointTopology.TOPO_T
    assert candidate.elements == (main, cross)
    assert candidate.info_for(main).role == "main"
    assert candidate.info_for(cross).role == "cross"


def test_get_connection_candidate_plates_carry_solved_distance_and_location():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    plate_b = Plate.from_outline_thickness(polyline_b, 1)
    candidate = get_connection_candidate(plate_a, plate_b, max_distance=None)
    solved = PlateConnectionSolver().find_topology(plate_a, plate_b, max_distance=None)
    assert type(candidate) is JointCandidate
    assert candidate.topology == solved.topology
    assert candidate.distance == solved.distance
    assert candidate.location == solved.location
    for plate in (plate_a, plate_b):
        assert candidate.info_for(plate).edge_index == solved.info_for(plate).edge_index
