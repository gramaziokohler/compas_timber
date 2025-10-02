import pytest

from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL

from compas_timber.connections import PlateJointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections.solver import PlateSolverResult
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


@pytest.fixture
def plates():
    """Create a basic TimberModel with two plates."""

    model = TimberModel()

    # Create two plates
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate1 = Plate.from_outline_thickness(polyline_a, 1)
    plate2 = Plate.from_outline_thickness(polyline_b, 1)

    model.add_element(plate1)
    model.add_element(plate2)

    return model

def test_flat_plate_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert plate_a.thickness == 1, "Expected plate thickness to match input thickness"
    assert plate_a.length == 10, "Expected plate length to be 10"
    assert plate_a.width == 20, "Expected plate width to be 20"

def test_sloped_plate_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert plate_a.frame.point == Point(0,10,0), "Expected plate frame to match input polyline"
    assert all([TOL.is_allclose(plate_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert TOL.is_close(plate_a.thickness, 1), "Expected plate thickness to match input thickness"
    assert TOL.is_close(plate_a.length, 14.1421356237), "Expected plate length to be 10*sqrt(2)"
    assert TOL.is_close(plate_a.width, 20), "Expected plate width to be 20"
