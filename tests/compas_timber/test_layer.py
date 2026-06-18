"""Tests for the Layer class and related Panel layer functionality."""

import pytest

from compas.data import json_dumps, json_loads
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import Layer
from compas_timber.elements import Panel
from compas_timber.model import TimberModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_panel():
    """10 x 20 panel, thickness 1, flat in XY — same outline ordering as test_panel.py."""
    outline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    return Panel.from_outline_thickness(outline_a, 1)


@pytest.fixture
def panel_with_layers(flat_panel):
    """The flat panel after define_core_layer(0.2, 0.8)."""
    flat_panel.define_core_layer(0.2, 0.8)
    return flat_panel


@pytest.fixture
def sloped_panel():
    """Panel sloped at 45° in the YZ plane; outline_a lies on y=10..20, z=0..10."""
    outline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    return Panel.from_outline_thickness(outline_a, 1)


@pytest.fixture
def offset_panel():
    """Flat 10x20 panel with thickness 1 translated to (100, 50, 30) — not at world origin."""
    outline_a = Polyline([Point(100, 50, 30), Point(100, 70, 30), Point(110, 70, 30), Point(110, 50, 30), Point(100, 50, 30)])
    return Panel.from_outline_thickness(outline_a, 1)


# ---------------------------------------------------------------------------
# 1. Layer basic construction
# ---------------------------------------------------------------------------


def test_layer_basic_construction(flat_panel):
    layer = Layer(flat_panel, 0, 0.5)
    assert TOL.is_close(layer.thickness, 0.5)
    for pt in layer.outline_a.points:
        assert TOL.is_close(pt[2], 0.0)
    for pt in layer.outline_b.points:
        assert TOL.is_close(pt[2], 0.5)


# ---------------------------------------------------------------------------
# 2. get_outlines_from_panel_range
# ---------------------------------------------------------------------------


def test_get_outlines_from_panel_range_start(flat_panel):
    outline_a, _ = Layer.get_outlines_from_panel_range(flat_panel, 0, 0)
    for pt_layer, pt_panel in zip(outline_a.points, flat_panel.plate_geometry.outline_a.points):
        assert TOL.is_allclose(pt_layer, pt_panel)


def test_get_outlines_from_panel_range_mid(flat_panel):
    outline_a, outline_b = Layer.get_outlines_from_panel_range(flat_panel, 0.4, 0.6)
    for pt in outline_a.points:
        assert TOL.is_close(pt[2], 0.4)
    for pt in outline_b.points:
        assert TOL.is_close(pt[2], 0.6)


def test_get_outlines_from_panel_range_end(flat_panel):
    _, outline_b = Layer.get_outlines_from_panel_range(flat_panel, 0, flat_panel.thickness)
    for pt_layer, pt_panel in zip(outline_b.points, flat_panel.plate_geometry.outline_b.points):
        assert TOL.is_allclose(pt_layer, pt_panel)


# ---------------------------------------------------------------------------
# 3. define_core_layer — full split
# ---------------------------------------------------------------------------


def test_define_core_layer_full_split(flat_panel):
    flat_panel.define_core_layer(0.2, 0.8)
    ext = flat_panel.exterior_layer
    core = flat_panel.core_layer
    inter = flat_panel.interior_layer

    assert ext is not None
    assert core is not None
    assert inter is not None

    assert TOL.is_close(ext.thickness, 0.2)
    assert TOL.is_close(core.thickness, 0.6)
    assert TOL.is_close(inter.thickness, 0.2)

    assert TOL.is_close(ext.start_level, 0.0)
    assert TOL.is_close(ext.end_level, 0.2)
    assert TOL.is_close(core.start_level, 0.2)
    assert TOL.is_close(core.end_level, 0.8)
    assert TOL.is_close(inter.start_level, 0.8)
    assert TOL.is_close(inter.end_level, 1.0)


# ---------------------------------------------------------------------------
# 4. define_core_layer — no exterior (start=0)
# ---------------------------------------------------------------------------


def test_define_core_layer_no_exterior(flat_panel):
    flat_panel.define_core_layer(0, 0.8)
    assert flat_panel.exterior_layer is None
    assert flat_panel.core_layer is not None
    assert flat_panel.interior_layer is not None
    assert TOL.is_close(flat_panel.core_layer.thickness, 0.8)
    assert TOL.is_close(flat_panel.interior_layer.thickness, 0.2)


# ---------------------------------------------------------------------------
# 5. define_core_layer — no interior (end=thickness)
# ---------------------------------------------------------------------------


def test_define_core_layer_no_interior(flat_panel):
    flat_panel.define_core_layer(0.2, flat_panel.thickness)
    assert flat_panel.exterior_layer is not None
    assert flat_panel.core_layer is not None
    assert flat_panel.interior_layer is None
    assert TOL.is_close(flat_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(flat_panel.core_layer.thickness, 0.8)


# ---------------------------------------------------------------------------
# 6. define_core_layer — invalid range raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start, end",
    [
        (0.5, 0.3),  # start >= end
        (-0.1, 0.8),  # start < 0
        (0.2, 1.5),  # end > thickness
        (0.5, 0.5),  # start == end
    ],
)
def test_define_core_layer_invalid_range(flat_panel, start, end):
    with pytest.raises(ValueError):
        flat_panel.define_core_layer(start, end)


# ---------------------------------------------------------------------------
# 7. Panel.layer_tree
# ---------------------------------------------------------------------------


def test_panel_layer_tree(panel_with_layers):
    tree = panel_with_layers.layer_tree
    assert (0,) in tree
    assert (1,) in tree
    assert (2,) in tree
    assert tree[(0,)] is panel_with_layers.exterior_layer
    assert tree[(1,)] is panel_with_layers.core_layer
    assert tree[(2,)] is panel_with_layers.interior_layer


def test_panel_layer_tree_no_exterior(flat_panel):
    flat_panel.define_core_layer(0, 0.8)
    tree = flat_panel.layer_tree
    assert len(tree) == 2
    assert tree[(0,)] is flat_panel.core_layer
    assert tree[(1,)] is flat_panel.interior_layer


# ---------------------------------------------------------------------------
# 8. Panel.layers
# ---------------------------------------------------------------------------


def test_panel_layers_full_split(panel_with_layers):
    assert len(list(panel_with_layers.layers)) == 3


def test_panel_layers_partial_split(flat_panel):
    flat_panel.define_core_layer(0, 0.8)
    assert len(list(flat_panel.layers)) == 2


# ---------------------------------------------------------------------------
# 9. Panel.get_leaf_layers — no crash with None boundaries
# ---------------------------------------------------------------------------


def test_get_leaf_layers_full_split(panel_with_layers):
    assert len(panel_with_layers.get_leaf_layers) == 3


def test_get_leaf_layers_no_exterior(flat_panel):
    flat_panel.define_core_layer(0, 0.8)
    leaves = flat_panel.get_leaf_layers  # must not crash when exterior_layer is None
    assert len(leaves) == 2


def test_get_leaf_layers_no_interior(flat_panel):
    flat_panel.define_core_layer(0.2, flat_panel.thickness)
    leaves = flat_panel.get_leaf_layers  # must not crash when interior_layer is None
    assert len(leaves) == 2


def test_get_leaf_layers_no_layers(flat_panel):
    assert flat_panel.get_leaf_layers == []


# ---------------------------------------------------------------------------
# 10. TimberModel.layers
# ---------------------------------------------------------------------------


def test_timber_model_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    layers = model.layers
    assert len(layers) == 3
    assert all(isinstance(layer, Layer) for layer in layers)


# ---------------------------------------------------------------------------
# 11. Panel.model setter — layers appear in model.elements() as children
# ---------------------------------------------------------------------------


def test_panel_model_setter_adds_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    all_elements = list(model.elements())
    assert len(all_elements) == 4  # panel + 3 layers
    children = list(panel_with_layers.children)
    assert panel_with_layers.exterior_layer in children
    assert panel_with_layers.core_layer in children
    assert panel_with_layers.interior_layer in children


# ---------------------------------------------------------------------------
# 12. Layer.sublayers setter — propagates to model
# ---------------------------------------------------------------------------


def test_layer_sublayers_setter_propagates_to_model(flat_panel):
    flat_panel.define_core_layer(0.2, 0.8)
    model = TimberModel()
    model.add_element(flat_panel)

    sub = Layer(flat_panel, 0.3, 0.6, name="Sub Layer")
    flat_panel.core_layer.sublayers = [sub]

    assert sub in list(model.elements())


# ---------------------------------------------------------------------------
# 13. Layer.set_extension_plane propagation
# ---------------------------------------------------------------------------


def test_set_extension_plane_propagates_to_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)

    # Edge 3 is the bottom edge (y=0); outward normal (0,-1,0)
    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    panel_with_layers.set_extension_plane(3, plane)

    for layer in [panel_with_layers.exterior_layer, panel_with_layers.core_layer, panel_with_layers.interior_layer]:
        if layer is not None:
            assert 3 in layer.plate_geometry._extension_planes


# ---------------------------------------------------------------------------
# 14. Layer.apply_edge_extensions propagation
# ---------------------------------------------------------------------------


def test_apply_edge_extensions_propagates_to_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)

    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    panel_with_layers.set_extension_plane(3, plane)

    before = {
        "ext": [list(pt) for pt in panel_with_layers.exterior_layer.outline_b.points],
        "core": [list(pt) for pt in panel_with_layers.core_layer.outline_b.points],
        "inter": [list(pt) for pt in panel_with_layers.interior_layer.outline_b.points],
    }

    panel_with_layers.apply_edge_extensions()

    for key, layer in [
        ("ext", panel_with_layers.exterior_layer),
        ("core", panel_with_layers.core_layer),
        ("inter", panel_with_layers.interior_layer),
    ]:
        after_pts = [list(pt) for pt in layer.outline_b.points]
        moved = any(not TOL.is_allclose(a, b) for a, b in zip(after_pts, before[key]))
        assert moved, "Expected layer {!r} outline_b to move after apply_edge_extensions".format(layer.name)


# ---------------------------------------------------------------------------
# 15. JSON round-trip of a standalone Layer
# ---------------------------------------------------------------------------


def test_layer_json_roundtrip(flat_panel):
    layer = Layer(flat_panel, 0.2, 0.7, name="test_layer")
    restored = json_loads(json_dumps(layer))

    assert isinstance(restored, Layer)
    assert TOL.is_close(restored.start_level, 0.2)
    assert TOL.is_close(restored.end_level, 0.7)
    assert TOL.is_close(restored.thickness, 0.5)
    assert restored.name == "test_layer"
    assert restored.panel is None  # expected after deserialization


# ---------------------------------------------------------------------------
# 16. JSON round-trip of a Panel with layers inside a TimberModel
# ---------------------------------------------------------------------------


def test_panel_with_layers_model_json_roundtrip(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)

    restored_model = json_loads(json_dumps(model))

    assert len(restored_model.panels) == 1
    assert len(restored_model.layers) == 3
    thicknesses = sorted(layer.thickness for layer in restored_model.layers)
    assert TOL.is_allclose(thicknesses, [0.2, 0.2, 0.6])


# ---------------------------------------------------------------------------
# 17. Sloped panel — layers are correctly positioned in world space
# ---------------------------------------------------------------------------


def test_sloped_panel_layer_thickness(sloped_panel):
    """Layer thicknesses are correct for a 45° sloped panel."""
    sloped_panel.define_core_layer(0.2, 0.8)
    assert TOL.is_close(sloped_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(sloped_panel.core_layer.thickness, 0.6)
    assert TOL.is_close(sloped_panel.interior_layer.thickness, 0.2)


def test_sloped_panel_layer_normal_matches_panel(sloped_panel):
    """Layer normals are parallel to the panel normal (world space)."""
    sloped_panel.define_core_layer(0.2, 0.8)
    model = TimberModel()
    model.add_element(sloped_panel)
    panel_normal = sloped_panel.normal
    for layer in sloped_panel.layers:
        assert TOL.is_allclose(layer.normal, panel_normal)


def test_sloped_panel_layer_outlines_interpolated(sloped_panel):
    """Layer outlines are linear interpolations between the panel's outlines (world space)."""
    sloped_panel.define_core_layer(0.2, 0.8)
    model = TimberModel()
    model.add_element(sloped_panel)

    panel_a_pts = sloped_panel.outline_a.points
    panel_b_pts = sloped_panel.outline_b.points
    t = sloped_panel.thickness

    for start, end, layer in [
        (0.0, 0.2, sloped_panel.exterior_layer),
        (0.2, 0.8, sloped_panel.core_layer),
        (0.8, 1.0, sloped_panel.interior_layer),
    ]:
        for pt_a_panel, pt_b_panel, pt_a_layer, pt_b_layer in zip(panel_a_pts, panel_b_pts, layer.outline_a.points, layer.outline_b.points):
            expected_a = pt_a_panel + (start / t) * (pt_b_panel - pt_a_panel)
            expected_b = pt_a_panel + (end / t) * (pt_b_panel - pt_a_panel)
            assert TOL.is_allclose(pt_a_layer, expected_a)
            assert TOL.is_allclose(pt_b_layer, expected_b)


# ---------------------------------------------------------------------------
# 18. Offset panel — layers are correctly positioned in world space
# ---------------------------------------------------------------------------


def test_offset_panel_layer_thickness(offset_panel):
    """Layer thicknesses are correct for a panel not at world origin."""
    offset_panel.define_core_layer(0.2, 0.8)
    assert TOL.is_close(offset_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(offset_panel.core_layer.thickness, 0.6)
    assert TOL.is_close(offset_panel.interior_layer.thickness, 0.2)


def test_offset_panel_layer_outlines_world_positions(offset_panel):
    """Layer outlines are at correct world-space positions for a panel translated to (100, 50, 30)."""
    offset_panel.define_core_layer(0.2, 0.8)
    model = TimberModel()
    model.add_element(offset_panel)

    panel_a_pts = offset_panel.outline_a.points
    panel_b_pts = offset_panel.outline_b.points
    t = offset_panel.thickness

    for start, end, layer in [
        (0.0, 0.2, offset_panel.exterior_layer),
        (0.2, 0.8, offset_panel.core_layer),
        (0.8, 1.0, offset_panel.interior_layer),
    ]:
        for pt_a_panel, pt_b_panel, pt_a_layer, pt_b_layer in zip(panel_a_pts, panel_b_pts, layer.outline_a.points, layer.outline_b.points):
            expected_a = pt_a_panel + (start / t) * (pt_b_panel - pt_a_panel)
            expected_b = pt_a_panel + (end / t) * (pt_b_panel - pt_a_panel)
            assert TOL.is_allclose(pt_a_layer, expected_a)
            assert TOL.is_allclose(pt_b_layer, expected_b)
