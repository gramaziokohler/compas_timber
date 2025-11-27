import pytest

from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL

from compas_timber.elements import Slab
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    """Create a basic TimberModel with two slabs."""

    model = TimberModel()

    # Create two slabs
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    slab_a = Slab.from_outline_thickness(polyline_a, 1)
    slab_b = Slab.from_outline_thickness(polyline_b, 1)

    model.add_element(slab_a)
    model.add_element(slab_b)

    return model


def test_flat_slab_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(polyline_a, 1)
    assert all([slab_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected slab to match input polyline"
    assert slab_a.thickness == 1, "Expected slab thickness to match input thickness"
    assert slab_a.length == 10, "Expected slab length to be 10"
    assert slab_a.width == 20, "Expected slab width to be 20"


def test_sloped_slab_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_a = Slab.from_outline_thickness(polyline_a, 1)
    assert slab_a.frame.point == Point(0, 10, 0), "Expected slab frame to match input polyline"
    assert all([TOL.is_allclose(slab_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(slab_a.outline_a.points))]), "Expected slab to match input polyline"
    assert TOL.is_close(slab_a.thickness, 1), "Expected slab thickness to match input thickness"
    assert TOL.is_close(slab_a.length, 14.1421356237), "Expected slab length to be 10*sqrt(2)"
    assert TOL.is_close(slab_a.width, 20), "Expected slab width to be 20"
