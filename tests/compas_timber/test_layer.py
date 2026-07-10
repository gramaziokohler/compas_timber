"""Tests for Layer, LayerDef, LayerStructure, and related Panel layer functionality."""

import pytest

from compas.data import json_dumps, json_loads
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import Layer
from compas_timber.elements import LayerDef
from compas_timber.elements import LayerStructure
from compas_timber.elements import Panel
from compas_timber.errors import FeatureApplicationError
from compas_timber.model import TimberModel
from compas_timber.panel_features import PanelFeature


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_panel():
    """10 x 20 panel, thickness 1, flat in XY."""
    outline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    return Panel.from_outline_thickness(outline_a, 1)


@pytest.fixture
def panel_with_layers(flat_panel):
    """Flat panel with 3-layer structure: exterior(0.2), core(0.6), interior(0.2)."""
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    return flat_panel


@pytest.fixture
def sloped_panel():
    """Panel sloped at 45° in the YZ plane; outline_a lies on y=10..20, z=0..10."""
    outline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    return Panel.from_outline_thickness(outline_a, 1)


@pytest.fixture
def offset_panel():
    """Flat 10x20 panel with thickness 1 translated to (100, 50, 30)."""
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
# 2. get_outlines_from_parent
# ---------------------------------------------------------------------------


def test_get_outlines_from_parent_start(flat_panel):
    outline_a, _ = Layer.get_outlines_from_parent(flat_panel, 0, 0)
    for pt_layer, pt_panel in zip(outline_a.points, flat_panel.plate_geometry.outline_a.points):
        assert TOL.is_allclose(pt_layer, pt_panel)


def test_get_outlines_from_parent_mid(flat_panel):
    outline_a, outline_b = Layer.get_outlines_from_parent(flat_panel, 0.4, 0.6)
    for pt in outline_a.points:
        assert TOL.is_close(pt[2], 0.4)
    for pt in outline_b.points:
        assert TOL.is_close(pt[2], 0.6)


def test_get_outlines_from_parent_end(flat_panel):
    _, outline_b = Layer.get_outlines_from_parent(flat_panel, 0, flat_panel.thickness)
    for pt_layer, pt_panel in zip(outline_b.points, flat_panel.plate_geometry.outline_b.points):
        assert TOL.is_allclose(pt_layer, pt_panel)


# ---------------------------------------------------------------------------
# 3. LayerStructure — default (single core)
# ---------------------------------------------------------------------------


def test_layer_structure_default_core(flat_panel):
    """A panel with default LayerStructure() gets one full-thickness 'core' layer."""
    assert flat_panel.core_layer is not None
    assert flat_panel.exterior_layer is None
    assert flat_panel.interior_layer is None
    assert TOL.is_close(flat_panel.core_layer.thickness, 1.0)
    assert flat_panel.core_layer.name == "core"


# ---------------------------------------------------------------------------
# 4. LayerStructure — full 3-layer split
# ---------------------------------------------------------------------------


def test_layer_structure_full_split(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
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
# 5. LayerStructure — no exterior
# ---------------------------------------------------------------------------


def test_layer_structure_no_exterior(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("core", 0.8),
            LayerDef("interior", 0.2),
        ]
    )
    assert flat_panel.exterior_layer is None
    assert flat_panel.core_layer is not None
    assert flat_panel.interior_layer is not None
    assert TOL.is_close(flat_panel.core_layer.thickness, 0.8)
    assert TOL.is_close(flat_panel.interior_layer.thickness, 0.2)


# ---------------------------------------------------------------------------
# 6. LayerStructure — no interior
# ---------------------------------------------------------------------------


def test_layer_structure_no_interior(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
        ]
    )
    assert flat_panel.exterior_layer is not None
    assert flat_panel.core_layer is not None
    assert flat_panel.interior_layer is None
    assert TOL.is_close(flat_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(flat_panel.core_layer.thickness, 0.8)


# ---------------------------------------------------------------------------
# 7. LayerStructure — validation errors
# ---------------------------------------------------------------------------


def test_layer_structure_multiple_fill_raises(flat_panel):
    """Two siblings with thickness=None should raise."""
    with pytest.raises(ValueError):
        flat_panel.layer_structure = LayerStructure(
            layer_defs=[
                LayerDef("exterior"),
                LayerDef("interior"),
            ]
        )


def test_layer_structure_thicknesses_exceed_total_raises(flat_panel):
    """Fixed thicknesses summing beyond panel thickness should raise."""
    with pytest.raises(ValueError):
        flat_panel.layer_structure = LayerStructure(
            layer_defs=[
                LayerDef("exterior", 0.6),
                LayerDef("core", 0.6),
            ]
        )


# ---------------------------------------------------------------------------
# 8. LayerStructure.get_path_for_name
# ---------------------------------------------------------------------------


def test_layer_structure_get_path_for_name_flat():
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    assert ls.get_path_for_name("exterior") == (0,)
    assert ls.get_path_for_name("core") == (1,)
    assert ls.get_path_for_name("interior") == (2,)
    assert ls.get_path_for_name("unknown") is None


def test_layer_structure_get_path_for_name_nested():
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef(
                "frame",
                sublayer_defs=[
                    LayerDef("service_void", 0.05),
                    LayerDef("insulation"),
                ],
            ),
            LayerDef("interior", 0.1),
        ]
    )
    assert ls.get_path_for_name("exterior") == (0,)
    assert ls.get_path_for_name("frame") == (1,)
    assert ls.get_path_for_name("service_void") == (1, 0)
    assert ls.get_path_for_name("insulation") == (1, 1)
    assert ls.get_path_for_name("interior") == (2,)


# ---------------------------------------------------------------------------
# 9. LayerStructure shared across multiple panels
# ---------------------------------------------------------------------------


def test_layer_structure_shared_across_panels():
    """Same LayerStructure instance can be attached to multiple panels independently."""
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    outline = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    p1 = Panel.from_outline_thickness(outline, 1.0)
    p2 = Panel.from_outline_thickness(outline, 2.0)

    p1.layer_structure = ls
    p2.layer_structure = ls

    assert p1.core_layer is not p2.core_layer
    assert TOL.is_close(p1.core_layer.thickness, 0.6)
    assert TOL.is_close(p2.core_layer.thickness, 1.6)


# ---------------------------------------------------------------------------
# 10. Panel named-layer properties
# ---------------------------------------------------------------------------


def test_panel_named_layers(panel_with_layers):
    layers = panel_with_layers.layers
    assert layers[0] is panel_with_layers.exterior_layer
    assert layers[1] is panel_with_layers.core_layer
    assert layers[2] is panel_with_layers.interior_layer


def test_panel_named_layers_partial(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("core", 0.8),
            LayerDef("interior", 0.2),
        ]
    )
    layers = flat_panel.layers
    assert len(layers) == 2
    assert layers[0] is flat_panel.core_layer
    assert layers[1] is flat_panel.interior_layer


# ---------------------------------------------------------------------------
# 11. Panel.layers
# ---------------------------------------------------------------------------


def test_panel_layers_full_split(panel_with_layers):
    assert len(list(panel_with_layers.layers)) == 3


def test_panel_layers_partial_split(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("core", 0.8),
            LayerDef("interior", 0.2),
        ]
    )
    assert len(list(flat_panel.layers)) == 2


# ---------------------------------------------------------------------------
# 12. Panel.get_leaf_layers
# ---------------------------------------------------------------------------


def test_get_leaf_layers_full_split(panel_with_layers):
    assert len(panel_with_layers.get_leaf_layers()) == 3


def test_get_leaf_layers_no_exterior(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("core", 0.8),
            LayerDef("interior", 0.2),
        ]
    )
    assert len(flat_panel.get_leaf_layers()) == 2


def test_get_leaf_layers_no_interior(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
        ]
    )
    assert len(flat_panel.get_leaf_layers()) == 2


def test_get_leaf_layers_default_core(flat_panel):
    """A fresh panel with the default LayerStructure has one leaf: the core layer."""
    assert len(flat_panel.get_leaf_layers()) == 1
    assert flat_panel.get_leaf_layers()[0].name == "core"


# ---------------------------------------------------------------------------
# 13. TimberModel.layers
# ---------------------------------------------------------------------------


def test_timber_model_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)
    layers = model.layers
    assert len(layers) == 3
    assert all(isinstance(layer, Layer) for layer in layers)


# ---------------------------------------------------------------------------
# 14. merge_layer_structure — layers appear in model.elements() as children
# ---------------------------------------------------------------------------


def test_merge_layer_structure_adds_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)
    all_elements = list(model.elements())
    assert len(all_elements) == 4  # panel + 3 layers
    children = list(panel_with_layers.children)
    assert panel_with_layers.exterior_layer in children
    assert panel_with_layers.core_layer in children
    assert panel_with_layers.interior_layer in children


# ---------------------------------------------------------------------------
# 15. Layer.sublayers setter — propagates to model
# ---------------------------------------------------------------------------


def test_layer_sublayers_setter_propagates_to_model(flat_panel):
    flat_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    model = TimberModel()
    model.add_element(flat_panel)
    flat_panel.merge_layer_structure(model)

    sub = Layer(flat_panel, 0.3, 0.6, name="Sub Layer")
    flat_panel.core_layer.sublayers = [sub]

    assert sub in list(model.elements())


# ---------------------------------------------------------------------------
# 16. Layer.set_extension_plane propagation
# ---------------------------------------------------------------------------


def test_set_extension_plane_propagates_to_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    panel_with_layers.set_extension_plane(3, plane)

    for layer in [panel_with_layers.exterior_layer, panel_with_layers.core_layer, panel_with_layers.interior_layer]:
        if layer is not None:
            assert 3 in layer.plate_geometry._extension_planes


# ---------------------------------------------------------------------------
# 17. Layer.apply_edge_extensions propagation
# ---------------------------------------------------------------------------


def test_apply_edge_extensions_propagates_to_layers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

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
# 18. JSON round-trip of a standalone Layer
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
# 19. JSON round-trip of a Panel with layers inside a TimberModel
# ---------------------------------------------------------------------------


def test_panel_with_layers_model_json_roundtrip(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    restored_model = json_loads(json_dumps(model))

    assert len(restored_model.panels) == 1
    assert len(restored_model.layers) == 3
    thicknesses = sorted(layer.thickness for layer in restored_model.layers)
    assert TOL.is_allclose(thicknesses, [0.2, 0.2, 0.6])


def test_panel_layer_structure_json_roundtrip(flat_panel):
    """layer_structure is preserved through Panel serialization."""
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    flat_panel.layer_structure = ls

    restored = json_loads(json_dumps(flat_panel))

    assert restored.exterior_layer is not None
    assert restored.core_layer is not None
    assert restored.interior_layer is not None
    assert TOL.is_close(restored.exterior_layer.thickness, 0.2)
    assert TOL.is_close(restored.core_layer.thickness, 0.6)
    assert TOL.is_close(restored.interior_layer.thickness, 0.2)


# ---------------------------------------------------------------------------
# 20. Sloped panel — layers are correctly positioned in world space
# ---------------------------------------------------------------------------


def test_sloped_panel_layer_thickness(sloped_panel):
    sloped_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    assert TOL.is_close(sloped_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(sloped_panel.core_layer.thickness, 0.6)
    assert TOL.is_close(sloped_panel.interior_layer.thickness, 0.2)


def test_sloped_panel_layer_normal_matches_panel(sloped_panel):
    sloped_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    model = TimberModel()
    model.add_element(sloped_panel)
    sloped_panel.merge_layer_structure(model)
    panel_normal = sloped_panel.normal
    for layer in sloped_panel.layers:
        assert TOL.is_allclose(layer.normal, panel_normal)


def test_sloped_panel_layer_outlines_interpolated(sloped_panel):
    sloped_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    model = TimberModel()
    model.add_element(sloped_panel)
    sloped_panel.merge_layer_structure(model)

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
# 21. Offset panel — layers are correctly positioned in world space
# ---------------------------------------------------------------------------


def test_offset_panel_layer_thickness(offset_panel):
    offset_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    assert TOL.is_close(offset_panel.exterior_layer.thickness, 0.2)
    assert TOL.is_close(offset_panel.core_layer.thickness, 0.6)
    assert TOL.is_close(offset_panel.interior_layer.thickness, 0.2)


def test_offset_panel_layer_outlines_world_positions(offset_panel):
    offset_panel.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    model = TimberModel()
    model.add_element(offset_panel)
    offset_panel.merge_layer_structure(model)

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


# ---------------------------------------------------------------------------
# 22. LayerDef — layer_path is assigned by LayerStructure
# ---------------------------------------------------------------------------


def test_layer_def_paths_flat():
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )
    assert ls.layer_defs[0].layer_path == (0,)
    assert ls.layer_defs[1].layer_path == (1,)
    assert ls.layer_defs[2].layer_path == (2,)


def test_layer_def_paths_nested():
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef(
                "frame",
                sublayer_defs=[
                    LayerDef("service_void", 0.05),
                    LayerDef("insulation"),
                ],
            ),
            LayerDef("interior", 0.1),
        ]
    )
    assert ls.layer_defs[0].layer_path == (0,)
    assert ls.layer_defs[1].layer_path == (1,)
    assert ls.layer_defs[1].sublayer_defs[0].layer_path == (1, 0)
    assert ls.layer_defs[1].sublayer_defs[1].layer_path == (1, 1)
    assert ls.layer_defs[2].layer_path == (2,)


# ---------------------------------------------------------------------------
# 23. Layer.layer_path delegates to its LayerDef
# ---------------------------------------------------------------------------


def test_layer_layer_path(panel_with_layers):
    assert panel_with_layers.exterior_layer.layer_path == (0,)
    assert panel_with_layers.core_layer.layer_path == (1,)
    assert panel_with_layers.interior_layer.layer_path == (2,)


# ---------------------------------------------------------------------------
# 24. layer_path survives JSON round-trip
# ---------------------------------------------------------------------------


def test_layer_path_survives_model_roundtrip(panel_with_layers):
    """layer_path is serialized on Layer and survives a model JSON round-trip."""
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    restored_model = json_loads(json_dumps(model))
    restored_panel_layers = restored_model.layers

    paths = {layer.name: layer.layer_path for layer in restored_panel_layers}
    assert paths["exterior"] == (0,)
    assert paths["core"] == (1,)
    assert paths["interior"] == (2,)


def test_layer_path_survives_standalone_panel_roundtrip(panel_with_layers):
    """layer_path is preserved when serializing and restoring a standalone Panel."""
    restored = json_loads(json_dumps(panel_with_layers))

    assert restored.layers[0].layer_path == (0,)
    assert restored.layers[1].layer_path == (1,)
    assert restored.layers[2].layer_path == (2,)


# ---------------------------------------------------------------------------
# 25. __repr__ / __str__
# ---------------------------------------------------------------------------


def test_layer_repr_and_str(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5, name="core")
    assert repr(layer) == "Layer(name=core, thickness=0.5)"
    assert str(layer) == "Layer(name=core, thickness=0.5)"


def test_layer_repr_deferred_has_no_thickness():
    """A deferred Layer (no end_level) reports thickness=None in its repr."""
    layer = Layer(name="deferred")
    assert repr(layer) == "Layer(name=deferred, thickness=None)"


# ---------------------------------------------------------------------------
# 26. sublayers passed directly to the constructor
# ---------------------------------------------------------------------------


def test_layer_constructor_sublayers_argument(flat_panel):
    sub = Layer(start_level=0.0, end_level=0.5, name="sub")
    layer = Layer(flat_panel, 0.0, 1.0, sublayers=[sub])
    assert layer.sublayers == [sub]
    assert sub._parent_ref is layer


# ---------------------------------------------------------------------------
# 27. plate_geometry getter/setter edge cases
# ---------------------------------------------------------------------------


def test_plate_geometry_setter_overrides_lazy_computation(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    original = layer.plate_geometry
    sentinel = object()
    layer.plate_geometry = sentinel
    assert layer.plate_geometry is sentinel
    assert layer.plate_geometry is not original


def test_plate_geometry_raises_without_any_parent():
    """A fully deferred Layer with no parent reference cannot compute geometry."""
    layer = Layer(start_level=0.0, end_level=0.5)
    with pytest.raises(AttributeError):
        layer.plate_geometry


def test_plate_geometry_lazy_computation_via_sublayers_wiring(flat_panel):
    """A deferred Layer wired as a sublayer computes its geometry lazily from its parent."""
    core = Layer(flat_panel, 0.0, 1.0)
    deferred = Layer(start_level=0.2, end_level=0.7, name="deferred")
    core.sublayers = [deferred]

    assert deferred._plate_geometry is None
    plate_geometry = deferred.plate_geometry
    assert plate_geometry is not None
    for pt in deferred.outline_a.points:
        assert TOL.is_close(pt[2], 0.2)
    for pt in deferred.outline_b.points:
        assert TOL.is_close(pt[2], 0.7)


# ---------------------------------------------------------------------------
# 28. panel property/setter
# ---------------------------------------------------------------------------


def test_panel_setter_standalone():
    layer = Layer(name="standalone")
    panel = object()
    layer.panel = panel
    assert layer.panel is panel


def test_panel_property_no_panel_ancestor_in_model(flat_panel):
    """A Layer added to the model tree without a Panel ancestor resolves .panel to None."""
    core = Layer(flat_panel, 0.0, 1.0)
    model = TimberModel()
    model.add_element(core)  # root element, no Panel ancestor
    sub = Layer(core, 0.0, 0.5)
    model.add_element(sub, parent=core)

    assert core.panel is None
    assert sub.panel is None


# ---------------------------------------------------------------------------
# 29. outlines / planes / edge_planes / center_height
# ---------------------------------------------------------------------------


def test_layer_outlines_tuple(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    assert layer.outlines == (layer.outline_a, layer.outline_b)


def test_layer_planes(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    plane_a, plane_b = layer.planes
    assert TOL.is_close(plane_a.point[2], 0.0)
    assert TOL.is_close(plane_b.point[2], 0.5)
    assert TOL.is_allclose(plane_a.normal, Vector(0, 0, 1))
    assert TOL.is_allclose(plane_b.normal, Vector(0, 0, 1))


def test_layer_edge_planes(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    edge_planes = layer.edge_planes
    assert set(edge_planes.keys()) == set(layer.plate_geometry.edge_planes.keys())
    for plane in edge_planes.values():
        assert isinstance(plane, Plane)


def test_layer_center_height(flat_panel):
    layer = Layer(flat_panel, 0.2, 0.6)
    assert TOL.is_close(layer.center_height, 0.4)


# ---------------------------------------------------------------------------
# 30. geometry property
# ---------------------------------------------------------------------------


def test_layer_geometry_getter_standalone(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    assert layer.model is None
    geometry = layer.geometry
    assert geometry is layer.modelgeometry


def test_layer_geometry_setter_raises(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    with pytest.raises(AttributeError):
        layer.geometry = object()


# ---------------------------------------------------------------------------
# 31. reset()
# ---------------------------------------------------------------------------


def test_layer_reset_clears_debug_info_and_geometry(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    layer = panel_with_layers.exterior_layer
    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    layer.set_extension_plane(3, plane)
    layer.apply_edge_extensions()
    layer.debug_info.append("some debug info")

    layer.reset()

    assert layer.debug_info == []
    assert layer.plate_geometry._extension_planes == {}


# ---------------------------------------------------------------------------
# 32. define_sublayers
# ---------------------------------------------------------------------------


def test_define_sublayers_exact_thicknesses(panel_with_layers):
    core = panel_with_layers.core_layer
    subs = core.define_sublayers([0.3, 0.3])
    assert len(subs) == 2
    assert TOL.is_close(subs[0].thickness, 0.3)
    assert TOL.is_close(subs[1].thickness, 0.3)
    assert TOL.is_close(subs[0].start_level, core.start_level)
    assert core.sublayers == subs


def test_define_sublayers_with_none_absorbs_remainder(panel_with_layers):
    core = panel_with_layers.core_layer  # thickness 0.6
    subs = core.define_sublayers([0.2, None, 0.1])
    assert len(subs) == 3
    assert TOL.is_close(subs[0].thickness, 0.2)
    assert TOL.is_close(subs[1].thickness, 0.3)
    assert TOL.is_close(subs[2].thickness, 0.1)


def test_define_sublayers_names(panel_with_layers):
    core = panel_with_layers.core_layer
    subs = core.define_sublayers([0.3, 0.3], names=["a", "b"])
    assert subs[0].name == "a"
    assert subs[1].name == "b"


def test_define_sublayers_appends_remainder_layer(panel_with_layers):
    """When no None is present and thicknesses don't fill the layer, an extra layer absorbs the remainder."""
    core = panel_with_layers.core_layer  # thickness 0.6
    subs = core.define_sublayers([0.2])
    assert len(subs) == 2
    assert TOL.is_close(subs[0].thickness, 0.2)
    assert TOL.is_close(subs[1].thickness, 0.4)


def test_define_sublayers_appends_remainder_layer_with_names(panel_with_layers):
    """The auto-appended remainder layer gets a None name when explicit names are given."""
    core = panel_with_layers.core_layer  # thickness 0.6
    subs = core.define_sublayers([0.2], names=["named"])
    assert len(subs) == 2
    assert subs[0].name == "named"
    assert subs[1].name != "named"
    assert TOL.is_close(subs[1].thickness, 0.4)


def test_define_sublayers_multiple_none_raises(panel_with_layers):
    core = panel_with_layers.core_layer
    with pytest.raises(ValueError):
        core.define_sublayers([None, None])


def test_define_sublayers_names_length_mismatch_raises(panel_with_layers):
    core = panel_with_layers.core_layer
    with pytest.raises(ValueError):
        core.define_sublayers([0.3, 0.3], names=["only_one"])


def test_define_sublayers_thicknesses_exceed_layer_raises(panel_with_layers):
    core = panel_with_layers.core_layer  # thickness 0.6
    with pytest.raises(ValueError):
        core.define_sublayers([0.5, 0.5])


def test_define_sublayers_without_panel_raises():
    layer = Layer(name="orphan", start_level=0.0, end_level=0.5)
    with pytest.raises(RuntimeError):
        layer.define_sublayers([0.5])


# ---------------------------------------------------------------------------
# 33. set_extension_plane / apply_edge_extensions recurse through sublayers
# ---------------------------------------------------------------------------


def test_set_extension_plane_recurses_through_nested_sublayers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    core = panel_with_layers.core_layer
    grandchildren = core.define_sublayers([0.3, None])

    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    core.set_extension_plane(3, plane)

    for child in grandchildren:
        assert 3 in child.plate_geometry._extension_planes


def test_apply_edge_extensions_recurses_through_nested_sublayers(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    core = panel_with_layers.core_layer
    grandchildren = core.define_sublayers([0.3, None])

    plane = Plane(Point(0, -1, 0), Vector(0, -1, 0))
    core.set_extension_plane(3, plane)

    before = [list(pt) for pt in grandchildren[0].outline_b.points]
    core.apply_edge_extensions()
    after = [list(pt) for pt in grandchildren[0].outline_b.points]

    moved = any(not TOL.is_allclose(a, b) for a, b in zip(before, after))
    assert moved


# ---------------------------------------------------------------------------
# 34. reset_computed_properties / clear_model_dependent_cache
# ---------------------------------------------------------------------------


def test_reset_computed_properties_clears_planes_and_computed_caches(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    layer.planes  # populate cache
    layer.aabb  # populate cache
    assert layer._planes is not None

    layer.reset_computed_properties()

    assert layer._planes is None
    assert layer._aabb is None


def test_clear_model_dependent_cache(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    layer.planes
    layer.aabb
    layer.obb
    layer.collision_mesh

    layer.clear_model_dependent_cache()

    assert layer._modeltransformation is None
    assert layer._modelgeometry is None
    assert layer._aabb is None
    assert layer._obb is None
    assert layer._collision_mesh is None
    assert layer._planes is None


# ---------------------------------------------------------------------------
# 35. compute_aabb / compute_obb / compute_collision_mesh
# ---------------------------------------------------------------------------


def test_compute_aabb(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    box = layer.compute_aabb()
    assert TOL.is_close(box.zsize, 0.5)
    assert sorted([round(box.xsize, 6), round(box.ysize, 6)]) == [10.0, 20.0]


def test_compute_aabb_inflate(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    box = layer.compute_aabb(inflate=1.0)
    assert TOL.is_close(box.zsize, 1.5)
    assert sorted([round(box.xsize, 6), round(box.ysize, 6)]) == [11.0, 21.0]


def test_compute_obb(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    obb = layer.compute_obb()
    assert TOL.is_close(obb.zsize, 0.5)


def test_compute_collision_mesh(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    mesh = layer.compute_collision_mesh()
    assert mesh.number_of_faces() > 0


# ---------------------------------------------------------------------------
# 36. compute_modelgeometry — standalone vs. in-model
# ---------------------------------------------------------------------------


def test_compute_modelgeometry_standalone_uses_transformation(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    assert layer.model is None
    geometry = layer.compute_modelgeometry()
    expected = layer.elementgeometry.transformed(layer.transformation)
    assert geometry.volume == pytest.approx(expected.volume)


def test_compute_modelgeometry_in_model_uses_modeltransformation(panel_with_layers):
    model = TimberModel()
    model.add_element(panel_with_layers)
    panel_with_layers.merge_layer_structure(model)

    layer = panel_with_layers.core_layer
    assert layer.model is not None
    geometry = layer.compute_modelgeometry()
    assert geometry is not None


# ---------------------------------------------------------------------------
# 37. compute_elementgeometry — feature application and error handling
# ---------------------------------------------------------------------------


class _RaisingFeature(PanelFeature):
    def apply(self, geometry, panel):
        raise FeatureApplicationError(None, geometry, "boom")


def test_compute_elementgeometry_without_features(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    geometry = layer.compute_elementgeometry(include_features=False)
    assert geometry is not None
    assert layer.debug_info == []


def test_compute_elementgeometry_collects_feature_application_errors(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    flat_panel.add_feature(_RaisingFeature(Frame.worldXY()))

    geometry = layer.compute_elementgeometry(include_features=True)

    assert geometry is not None
    assert len(layer.debug_info) == 1
    assert isinstance(layer.debug_info[0], FeatureApplicationError)


def test_compute_elementgeometry_include_features_false_skips_panel_features(flat_panel):
    layer = Layer(flat_panel, 0.0, 0.5)
    flat_panel.add_feature(_RaisingFeature(Frame.worldXY()))

    layer.compute_elementgeometry(include_features=False)

    assert layer.debug_info == []


# ---------------------------------------------------------------------------
# 38. LayerDef / LayerStructure __repr__
# ---------------------------------------------------------------------------


def test_layer_def_repr():
    layer_def = LayerDef(name="core", thickness=0.5)
    assert repr(layer_def) == "LayerDef(name='core', thickness=0.5, path=())"


def test_layer_structure_repr():
    ls = LayerStructure(layer_defs=[LayerDef("core")])
    assert repr(ls) == "LayerStructure(layer_defs=[LayerDef(name='core', thickness=None, path=(0,))])"


# ---------------------------------------------------------------------------
# 39. LayerStructure.attach with nested sublayer_defs
# ---------------------------------------------------------------------------


def test_layer_structure_attach_with_nested_sublayer_defs(flat_panel):
    ls = LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef(
                "frame",
                sublayer_defs=[
                    LayerDef("service_void", 0.1),
                    LayerDef("insulation"),
                ],
            ),
            LayerDef("interior", 0.1),
        ]
    )
    flat_panel.layer_structure = ls

    frame_layer = next(layer for layer in flat_panel.layers if layer.name == "frame")
    assert len(frame_layer.sublayers) == 2
    service_void, insulation = frame_layer.sublayers
    assert service_void.name == "service_void"
    assert TOL.is_close(service_void.thickness, 0.1)
    assert insulation.name == "insulation"
    assert TOL.is_close(insulation.thickness, 0.6)
