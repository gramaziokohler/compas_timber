"""Tests for PanelLLayerButtJoint (connections/panel_layer_butt_joint.py)."""

from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.connections import JointTopology
from compas_timber.connections import PanelLButtJoint
from compas_timber.connections import PanelLLayerButtJoint
from compas_timber.elements import LayerDef
from compas_timber.elements import LayerStructure
from compas_timber.elements import Panel
from compas_timber.model import TimberModel


def _corner_panels():
    """Two 10x10 panels meeting edge-to-edge at a 45 degree corner.

    panel_a's segment 1 (from (0,10,0) to (10,10,0)) meets panel_b's segment 0
    (from (0,10,0) to (10,10,0)).
    """
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    return panel_a, panel_b


def _three_layer_structure():
    return LayerStructure(
        layer_defs=[
            LayerDef("exterior", 0.2),
            LayerDef("core"),
            LayerDef("interior", 0.2),
        ]
    )


def _make_joint(panel_a, panel_b):
    return PanelLLayerButtJoint(panel_a, panel_b, topology=JointTopology.TOPO_EDGE_EDGE, a_segment_index=1, b_segment_index=0)


# ---------------------------------------------------------------------------
# main_panel / cross_panel / __repr__
# ---------------------------------------------------------------------------


def test_main_and_cross_panel_properties():
    panel_a, panel_b = _corner_panels()
    joint = _make_joint(panel_a, panel_b)
    assert joint.main_panel is panel_a
    assert joint.cross_panel is panel_b


def test_repr_names_the_correct_class_and_topology():
    panel_a, panel_b = _corner_panels()
    joint = _make_joint(panel_a, panel_b)
    text = repr(joint)
    assert text.startswith("PanelLLayerButtJoint(")
    assert "TOPO_EDGE_EDGE" in text


# ---------------------------------------------------------------------------
# add_extensions — full 3-layer split on both panels
# ---------------------------------------------------------------------------


def test_add_extensions_creates_butt_joint_per_layer_pair():
    panel_a, panel_b = _corner_panels()
    panel_a.layer_structure = _three_layer_structure()
    panel_b.layer_structure = _three_layer_structure()

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()

    for name in ("exterior_layer", "core_layer", "interior_layer"):
        layer_a = getattr(panel_a, name)
        layer_b = getattr(panel_b, name)
        assert 1 in layer_a.plate_geometry._extension_planes
        assert 0 in layer_b.plate_geometry._extension_planes


def test_add_extensions_does_not_touch_panel_level_geometry():
    """The panel-level plate_geometry is untouched; only its layers are extended."""
    panel_a, panel_b = _corner_panels()
    panel_a.layer_structure = _three_layer_structure()
    panel_b.layer_structure = _three_layer_structure()

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()

    assert panel_a.plate_geometry._extension_planes == {}
    assert panel_b.plate_geometry._extension_planes == {}


def test_add_extensions_applies_and_moves_layer_outlines():
    """Layer.outline_a/outline_b resolve correctly in world space only once part of a model tree."""
    panel_a, panel_b = _corner_panels()
    panel_a.layer_structure = _three_layer_structure()
    panel_b.layer_structure = _three_layer_structure()

    model = TimberModel()
    model.add_elements([panel_a, panel_b])
    panel_a.merge_layer_structure(model)
    panel_b.merge_layer_structure(model)

    core_before = [list(pt) for pt in panel_a.core_layer.outline_b.points]

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()
    panel_a.apply_edge_extensions()
    panel_b.apply_edge_extensions()

    core_after = [list(pt) for pt in panel_a.core_layer.outline_b.points]
    assert core_before != core_after


# ---------------------------------------------------------------------------
# add_extensions — only the default core layer is present
# ---------------------------------------------------------------------------


def test_add_extensions_default_layer_structure_only_core():
    """With the default LayerStructure (single 'core', no exterior/interior), only the core pair is joined."""
    panel_a, panel_b = _corner_panels()
    assert panel_a.exterior_layer is None
    assert panel_a.interior_layer is None
    assert panel_b.exterior_layer is None
    assert panel_b.interior_layer is None

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()

    assert 1 in panel_a.core_layer.plate_geometry._extension_planes
    assert 0 in panel_b.core_layer.plate_geometry._extension_planes


# ---------------------------------------------------------------------------
# add_extensions — asymmetric layer structures (one panel missing exterior)
# ---------------------------------------------------------------------------


def test_add_extensions_skips_layer_missing_on_either_panel():
    panel_a, panel_b = _corner_panels()
    panel_a.layer_structure = _three_layer_structure()
    panel_b.layer_structure = LayerStructure(
        layer_defs=[
            LayerDef("core", 0.8),
            LayerDef("interior", 0.2),
        ]
    )
    assert panel_b.exterior_layer is None

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()

    # core and interior are present on both panels -> extended
    assert 1 in panel_a.core_layer.plate_geometry._extension_planes
    assert 0 in panel_b.core_layer.plate_geometry._extension_planes
    assert 1 in panel_a.interior_layer.plate_geometry._extension_planes
    assert 0 in panel_b.interior_layer.plate_geometry._extension_planes

    # exterior is missing on panel_b -> panel_a's exterior layer is left untouched
    assert panel_a.exterior_layer.plate_geometry._extension_planes == {}


# ---------------------------------------------------------------------------
# add_extensions — sub-joints are PanelLButtJoint instances wired to the right layers
# ---------------------------------------------------------------------------


def test_sub_joints_are_panel_l_butt_joints_between_matching_layers(monkeypatch):
    panel_a, panel_b = _corner_panels()
    panel_a.layer_structure = _three_layer_structure()
    panel_b.layer_structure = _three_layer_structure()

    created = []
    original_init = PanelLButtJoint.__init__

    def recording_init(self, *args, **kwargs):
        created.append(kwargs)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(PanelLButtJoint, "__init__", recording_init)

    joint = _make_joint(panel_a, panel_b)
    joint.add_extensions()

    assert len(created) == 3
    pairs = [(kwargs["panel_a"], kwargs["panel_b"]) for kwargs in created]
    assert (panel_b.interior_layer, panel_a.interior_layer) in pairs
    assert (panel_a.core_layer, panel_b.core_layer) in pairs
    assert (panel_b.exterior_layer, panel_a.exterior_layer) in pairs
