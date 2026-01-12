import pytest

from compas.data import json_dumps, json_loads

from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL

from compas_timber.elements import Panel
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    """Create a basic TimberModel with two panels."""

    model = TimberModel()

    # Create two panels
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1, name="Best Panel")
    panel_b = Panel.from_outline_thickness(polyline_b, 1, name="Second Best Panel")

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


def test_copy_panel_model(model):
    model_copy = json_loads(json_dumps(model))

    assert len(list(model_copy.elements())) == len(list(model.elements())), "Expected copied model to have same number of elements"

    for original, copy in zip(model.panels, model_copy.panels):
        assert isinstance(copy, Panel)
        assert TOL.is_close(original.thickness, copy.thickness)
        assert original.frame == copy.frame
        assert TOL.is_close(original.width, copy.width)
        assert TOL.is_close(original.length, copy.length)
        assert original.name == copy.name
