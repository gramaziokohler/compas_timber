"""Placement of elements nested in the model tree: transforming an ancestor, (de)serialization, and joint re-processing."""

import math

import pytest
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Rotation
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import distance_point_plane
from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.elements import LayerDefinition
from compas_timber.elements import LayerStructure
from compas_timber.elements import Panel
from compas_timber.model import TimberModel

T = Translation.from_vector([500, -300, 1000]) * Rotation.from_axis_and_angle([0, 0, 1], math.radians(35))


def assert_same_frame(a, b):
    assert TOL.is_allclose(a.point, b.point)
    assert TOL.is_allclose(a.xaxis, b.xaxis)
    assert TOL.is_allclose(a.yaxis, b.yaxis)


def assert_same_plane(a, b):
    assert TOL.is_zero(distance_point_plane(a.point, b))
    assert TOL.is_allclose(a.normal.unitized(), b.normal.unitized())


@pytest.fixture
def panel_model():
    model = TimberModel()
    outline = Polyline([Point(1000, 0, 0), Point(4000, 0, 0), Point(4000, 2400, 0), Point(1000, 2400, 0), Point(1000, 0, 0)])
    panel = Panel.from_outline_thickness(outline, 200)
    panel.layer_structure = LayerStructure(layer_defs=[LayerDefinition("exterior", 50), LayerDefinition("core"), LayerDefinition("interior", 50)])
    model.add_element(panel)
    panel.merge_layer_structure(model)
    # beams are placed in the panel's local coordinates
    beam_a = Beam.from_centerline(Line(Point(0, 0, 0), Point(1200, 0, 0)), 80, 160)
    beam_b = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 1200, 0)), 80, 160)
    model.add_element(beam_a, parent=panel)
    model.add_element(beam_b, parent=panel)
    return model, panel, beam_a, beam_b


# ==========================================================================
# transforming an ancestor
# ==========================================================================


def test_model_transform_moves_panel_children(panel_model):
    model, panel, beam_a, beam_b = panel_model
    elements = [panel, beam_a, beam_b, *panel.layers]
    before = [element.frame.point for element in elements]

    model.transform(Translation.from_vector([0, 0, 250]))

    for element, point in zip(elements, before):
        assert TOL.is_allclose(element.frame.point, point + Vector(0, 0, 250))
