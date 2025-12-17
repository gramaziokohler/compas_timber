import pytest

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Frame
from compas.tolerance import TOL

from compas_timber.elements import Panel
from compas_timber.elements.beam import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    """Create a basic TimberModel with two panels."""

    model = TimberModel()

    # Create two panels
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    model.add_element(panel_a)
    model.add_element(panel_b)

    return model


def test_flat_panel_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert panel_a.thickness == 1, "Expected panel thickness to match input thickness"
    assert panel_a.length == 10, "Expected panel length to be 10"
    assert panel_a.width == 20, "Expected panel width to be 20"


def test_sloped_panel_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    assert panel_a.frame.point == Point(0, 10, 0), "Expected panel frame to match input polyline"
    assert all([TOL.is_allclose(panel_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert TOL.is_close(panel_a.thickness, 1), "Expected panel thickness to match input thickness"
    assert TOL.is_close(panel_a.length, 14.1421356237), "Expected panel length to be 10*sqrt(2)"
    assert TOL.is_close(panel_a.width, 20), "Expected panel width to be 20"

def test_panel_addition_to_model(model):
    panels = model.panels
    assert panels[0].modeltransformation == panels[0].transformation, "Expected panel model transformation to match panel transformation"
    assert panels[1].modeltransformation == panels[1].transformation, "Expected panel model transformation to match panel transformation"
    assert len(list(model.elements())) == 2, "Expected model to contain two panels"
    assert all(isinstance(element, Panel) for element in model.elements()), "Expected all elements in the model to be panels"

def test_add_beam_to_panel(model):
    beam = Beam(Frame.worldXY(), length=5, width=0.3, height=0.5, name="Beam 1")
    model.add_element(beam, parent=model.panels[1])
    assert len(list(model.elements())) == 3, "Expected model to contain two panels"
    assert beam in model.panels[1].children, "Expected beam to be a child of the panel"
    assert beam.modeltransformation == model.panels[1].transformation, "Expected beam model transformation to match panel transformation"
