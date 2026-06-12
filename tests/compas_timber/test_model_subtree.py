"""Tests for TimberModel subtree surgery methods:
    remove_element_subtree, _detach_subtree, _attach_subtree,
    extract_model_from_parent, merge_model.
"""
import pytest

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import LButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.model import TimberModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_beam(x=0.0):
    frame = Frame(Point(x, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    return Beam(frame, length=1.0, width=0.1, height=0.1)


def make_panel():
    return Panel(Frame.worldXY(), length=2.0, width=1.0, thickness=0.1)


def _flat_model():
    """Model with two root-level beams and a joint between them."""
    model = TimberModel()
    b1 = make_beam(x=0)
    b2 = make_beam(x=2)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


def _hierarchy_model():
    """Panel (root) → [beam_a, beam_b] with a joint between the two beams."""
    model = TimberModel()
    panel = make_panel()
    beam_a = make_beam(x=0)
    beam_b = make_beam(x=2)
    model.add_element(panel)
    model.add_element(beam_a, parent=panel)
    model.add_element(beam_b, parent=panel)
    return model, panel, beam_a, beam_b


# ===========================================================================
# remove_element_subtree
# ===========================================================================


def test_remove_element_subtree_removes_all_descendants():
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(panel)

    elements = list(model.elements())
    assert beam_a not in elements
    assert beam_b not in elements


def test_remove_element_subtree_keeps_parent():
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(panel)

    assert panel in list(model.elements())


def test_remove_element_subtree_panel_has_no_children_after():
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(panel)

    assert panel.children == []


def test_remove_element_subtree_clears_cache_on_removed_elements():
    model, panel, beam_a, beam_b = _hierarchy_model()
    # Warm the cache first
    _ = beam_a.modeltransformation
    _ = beam_a.aabb

    model.remove_element_subtree(panel)

    assert beam_a._modeltransformation is None
    assert beam_a._aabb is None


def test_remove_element_subtree_removes_joints_spanning_only_descendants(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, panel, beam_a, beam_b = _hierarchy_model()
    LButtJoint.create(model, beam_a, beam_b)
    assert len(list(model.joints)) == 1

    model.remove_element_subtree(panel)

    assert len(list(model.joints)) == 0


def test_remove_element_subtree_leaf_element():
    """Calling on a leaf (no children) removes nothing — no-op."""
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(beam_a)

    elements = list(model.elements())
    assert beam_a in elements
    assert panel in elements
    assert beam_b in elements


# ===========================================================================
# _detach_subtree / _attach_subtree round-trip
# ===========================================================================


def test_detach_subtree_no_parent_empties_model():
    model, panel, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree()

    assert len(list(model.elements())) == 0


def test_detach_subtree_with_parent_removes_only_children():
    model, panel, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree(panel)

    elements = list(model.elements())
    assert panel in elements
    assert beam_a not in elements
    assert beam_b not in elements


def test_detach_subtree_returns_correct_tuples_for_flat_model():
    model, b1, b2 = _flat_model()

    tuples, joints = model._detach_subtree()

    # All top-level elements should be recorded under None
    assert len(tuples) == 1
    parent, children = tuples[0]
    assert parent is None
    assert set(children) == {b1, b2}


def test_detach_subtree_returns_correct_tuples_for_hierarchy():
    model, panel, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree()

    # Tuple 0: (None, [panel]) — top-level
    # Tuple 1: (panel, [beam_a, beam_b]) — panel's children
    assert len(tuples) == 2
    parents = {t[0] for t in tuples}
    assert None in parents
    assert panel in parents


def test_detach_subtree_captures_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = _flat_model()
    joint = LButtJoint.create(model, b1, b2)

    tuples, joints = model._detach_subtree()

    assert joint in joints
    assert len(list(model.joints)) == 0


def test_attach_subtree_restores_elements():
    model, panel, beam_a, beam_b = _hierarchy_model()
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    elements = list(new_model.elements())
    assert panel in elements
    assert beam_a in elements
    assert beam_b in elements


def test_attach_subtree_restores_hierarchy():
    model, panel, beam_a, beam_b = _hierarchy_model()
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    assert beam_a in panel.children
    assert beam_b in panel.children


def test_attach_subtree_restores_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = _flat_model()
    joint = LButtJoint.create(model, b1, b2)
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    assert len(list(new_model.joints)) == 1
    assert joint in new_model.joints


def test_attach_subtree_does_not_add_joints_twice(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = _flat_model()
    LButtJoint.create(model, b1, b2)
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    assert len(list(new_model.joints)) == 1


def test_attach_subtree_under_parent():
    """_attach_subtree with a parent arg should root detached elements under that parent."""
    model, b1, b2 = _flat_model()
    tuples, joints = model._detach_subtree()

    target_model = TimberModel()
    root_panel = make_panel()
    target_model.add_element(root_panel)
    target_model._attach_subtree(tuples, parent=root_panel)

    assert b1 in root_panel.children
    assert b2 in root_panel.children


# ===========================================================================
# extract_model_from_parent
# ===========================================================================


def test_extract_model_from_parent_returns_new_model():
    model, panel, beam_a, beam_b = _hierarchy_model()

    extracted = model.extract_model_from_parent(panel)

    assert extracted is not model
    assert isinstance(extracted, TimberModel)


def test_extract_model_from_parent_new_model_contains_children():
    model, panel, beam_a, beam_b = _hierarchy_model()

    extracted = model.extract_model_from_parent(panel)

    elements = list(extracted.elements())
    assert beam_a in elements
    assert beam_b in elements


def test_extract_model_from_parent_panel_stays_in_original():
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.extract_model_from_parent(panel)

    assert panel in list(model.elements())


def test_extract_model_from_parent_children_leave_original():
    model, panel, beam_a, beam_b = _hierarchy_model()

    model.extract_model_from_parent(panel)

    elements = list(model.elements())
    assert beam_a not in elements
    assert beam_b not in elements


def test_extract_model_from_parent_preserves_hierarchy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model = TimberModel()
    panel = make_panel()
    beam_a = make_beam(x=0)
    beam_b = make_beam(x=2)
    inner_panel = make_panel()
    inner_beam = make_beam(x=4)
    model.add_element(panel)
    model.add_element(beam_a, parent=panel)
    model.add_element(beam_b, parent=panel)
    model.add_element(inner_panel, parent=beam_a)
    model.add_element(inner_beam, parent=inner_panel)

    extracted = model.extract_model_from_parent(panel)

    assert inner_beam in inner_panel.children
    assert inner_panel in beam_a.children


def test_extract_model_from_parent_moves_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, panel, beam_a, beam_b = _hierarchy_model()
    joint = LButtJoint.create(model, beam_a, beam_b)

    extracted = model.extract_model_from_parent(panel)

    assert joint in extracted.joints
    assert len(list(model.joints)) == 0


# ===========================================================================
# merge_model
# ===========================================================================


def test_merge_model_moves_all_elements():
    source, panel, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    elements = list(target.elements())
    assert panel in elements
    assert beam_a in elements
    assert beam_b in elements


def test_merge_model_empties_source():
    source, panel, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    assert len(list(source.elements())) == 0


def test_merge_model_preserves_hierarchy():
    source, panel, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    assert beam_a in panel.children
    assert beam_b in panel.children


def test_merge_model_moves_joints_exactly_once(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    source, b1, b2 = _flat_model()
    LButtJoint.create(source, b1, b2)
    target = TimberModel()

    target.merge_model(source)

    assert len(list(target.joints)) == 1


def test_merge_model_with_parent_roots_under_parent():
    source, b1, b2 = _flat_model()
    target = TimberModel()
    root_panel = make_panel()
    target.add_element(root_panel)

    target.merge_model(source, parent=root_panel)

    assert b1 in root_panel.children
    assert b2 in root_panel.children


def test_merge_model_source_joints_cleared(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    source, b1, b2 = _flat_model()
    LButtJoint.create(source, b1, b2)
    target = TimberModel()

    target.merge_model(source)

    assert len(list(source.joints)) == 0
