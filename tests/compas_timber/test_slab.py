import pytest

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Frame
from compas.tolerance import TOL

from compas_timber.elements import Slab
from compas_timber.elements.beam import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    """Create a basic TimberModel with two plates."""

    model = TimberModel()

    # Create two plates
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


def test_slab_addition_to_model(model):
    slabs = model.slabs
    assert slabs[0].modeltransformation == slabs[0].transformation, "Expected slab model transformation to match slab transformation"
    assert slabs[1].modeltransformation == slabs[1].transformation, "Expected slab model transformation to match slab transformation"
    assert len(list(model.elements())) == 2, "Expected model to contain two slabs"
    assert all(isinstance(element, Slab) for element in model.elements()), "Expected all elements in the model to be slabs"


def test_add_beam_to_slab(model):
    beam = Beam(Frame.worldXY(), length=5, width=0.3, height=0.5, name="Beam 1")
    model.add_element(beam, parent=model.slabs[1])
    assert len(list(model.elements())) == 3, "Expected model to contain two slabs"
    assert beam in model.slabs[1].children, "Expected beam to be a child of the slab"
    assert beam.modeltransformation == model.slabs[1].transformation, "Expected beam model transformation to match slab transformation"
