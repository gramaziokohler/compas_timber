import pytest

from compas.data import json_dumps, json_loads

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Plane
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Vector
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
    expected_edge_planes = [([0, 0, 0], [-1, 0, 0]), ([0, 20, 0], [0, 1, 0]), ([10, 20, 0], [1, 0, 0]), ([10, 0, 0], [0, -1, 0])]
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert panel_a.thickness == 1, "Expected panel thickness to match input thickness"
    assert panel_a.length == 10, "Expected panel length to be 10"
    assert panel_a.width == 20, "Expected panel width to be 20"
    assert TOL.is_allclose(panel_a.normal, [0, 0, 1]), "Expected the normal to be the world Z-axis"
    for expected, plane in zip(expected_edge_planes, panel_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    for obb_pt, expected_pt in zip(panel_a.obb.points, Box.from_points([Point(0, 0, 0), Point(10, 20, 1)]).points):
        assert TOL.is_allclose(obb_pt, expected_pt)


def test_sloped_panel_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [
        ([0, 10, 0], [0, -0.707106781, -0.707106781]),
        ([10, 10, 0], [0.81649658, -0.40824829, -0.40824829]),
        ([20, 20, 10], [0, 0.707106781, 0.707106781]),
        ([0, 20, 10], [-1, 0, 0]),
    ]

    expected_obb = Box(
        xsize=14.142135623730951,
        ysize=20.0,
        zsize=1.0,
        frame=Frame(
            point=Point(x=10.0, y=15.353553390593273, z=4.646446609406729), xaxis=Vector(x=0.0, y=0.7071067811865475, z=0.7071067811865476), yaxis=Vector(x=1.0, y=0.0, z=0.0)
        ),
    )

    assert panel_a.frame.point == Point(0, 10, 0), "Expected panel frame to match input polyline"
    assert all([TOL.is_allclose(panel_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert TOL.is_close(panel_a.thickness, 1), "Expected panel thickness to match input thickness"
    assert TOL.is_close(panel_a.length, 14.1421356237), "Expected panel length to be 10*sqrt(2)"
    assert TOL.is_close(panel_a.width, 20), "Expected panel width to be 20"
    assert TOL.is_allclose(panel_a.normal, [0, 0.707106781, -0.707106781]), "Expected the normal to be at 45 degrees"
    for expected, plane in zip(expected_edge_planes, panel_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    assert TOL.is_allclose(expected_obb.frame.point, panel_a.obb.frame.point)
    assert TOL.is_allclose(expected_obb.frame.xaxis, panel_a.obb.frame.xaxis)
    assert TOL.is_allclose(expected_obb.frame.yaxis, panel_a.obb.frame.yaxis)
    assert TOL.is_close(expected_obb.xsize, panel_a.obb.xsize)
    assert TOL.is_close(expected_obb.ysize, panel_a.obb.ysize)
    assert TOL.is_close(panel_a.obb.zsize, 1.0)


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


def test_panel_serialization_with_attributes_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1, custom_attribute="custom_value", another_attribute=42)

    deserialized = json_loads(json_dumps(panel_a))

    assert deserialized.thickness == 1
    assert deserialized.length == 10
    assert deserialized.width == 20
    assert deserialized.attributes["custom_attribute"] == "custom_value"
    assert deserialized.attributes["another_attribute"] == 42


def test_panel_serialization_with_attributes():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    panel_a.attributes["custom_attribute"] = "custom_value"
    panel_a.attributes["another_attribute"] = 42

    deserialized = json_loads(json_dumps(panel_a))

    assert deserialized.thickness == 1
    assert deserialized.length == 10
    assert deserialized.width == 20
    assert deserialized.attributes["custom_attribute"] == "custom_value"
    assert deserialized.attributes["another_attribute"] == 42


def test_from_outline_thickness():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    panel_a = Panel.from_outlines(polyline_a, polyline_b)
    panel_b = Panel.from_outline_thickness(polyline_a, 1)

    for pt_a, pt_b in zip(panel_a.outline_b, panel_b.outline_b):
        assert TOL.is_allclose(pt_a, pt_b)


def test_set_extension_plane():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = Panel.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    plane_copies = [plane.copy() for plane in pg.edge_planes.values()]
    assert all([TOL.is_allclose(planes[i].normal, plane_copies[i].normal) for i in range(0, 3)])
    assert TOL.is_allclose(plane.normal, plane_copies[3].normal)
    assert not TOL.is_allclose(planes[3].normal, plane_copies[3].normal)


def test_apply_and_remove_exensions():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = Panel.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]

    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(polyline_b))])
    pg.remove_blank_extension()
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])
    for i in range(len(planes)):
        assert TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal)


def test_apply_and_remove_exensions_with_index():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = Panel.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(2)  # removing extension at index 2 should not affect index 3
    assert TOL.is_allclose(plane.normal, pg.edge_planes[3].normal)
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(3)  # removing extension at index 3 revert to original
    assert all([TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal) for i in range(len(planes))])
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])
