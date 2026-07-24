import pytest
from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.connections import get_connection_candidate
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import get_connection_candidate
from compas_timber.connections.candidate_dispatch import find_connection_handler
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


def test_find_connection_handler_beam_beam(beam):
    assert find_connection_handler(beam, beam) is ConnectionSolver


def test_find_connection_handler_plate_plate(plate):
    assert find_connection_handler(plate, plate) is PlateConnectionSolver


def test_find_connection_handler_panel_panel(panel):
    assert find_connection_handler(panel, panel) is PlateConnectionSolver


def test_find_connection_handler_unsupported_pair_returns_none(beam, plate):
    assert find_connection_handler(beam, plate) is None


def test_get_connection_candidate_unsupported_pair_returns_none_without_solving(beam, plate):
    """An unregistered type combination should short-circuit to None without invoking any solver."""
    assert get_connection_candidate(beam, plate, max_distance=1.0) is None
