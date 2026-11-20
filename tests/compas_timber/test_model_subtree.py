"""Tests for TimberModel subtree surgery methods:
remove_element_subtree, _detach_subtree, _attach_subtree,
extract_model_from_parent, merge_model.
"""

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import LButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_beam(x=0.0):
    frame = Frame(Point(x, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    return Beam(frame, length=1.0, width=0.1, height=0.1)


def make_parent():
    return Plate(Frame.worldXY(), length=2.0, width=1.0, thickness=0.1)


def _flat_model():
    """Model with two root-level beams and a joint between them."""
    model = TimberModel()
    b1 = make_beam(x=0)
    b2 = make_beam(x=2)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


def _hierarchy_model():
    """Parent (root) → [beam_a, beam_b] with a joint between the two beams."""
    model = TimberModel()
    parent = make_parent()
    beam_a = make_beam(x=0)
    beam_b = make_beam(x=2)
    model.add_element(parent)
    model.add_element(beam_a, parent=parent)
    model.add_element(beam_b, parent=parent)
    return model, parent, beam_a, beam_b


# ===========================================================================
# remove_element_subtree
# ===========================================================================


def test_remove_element_subtree_removes_all_descendants():
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(parent)

    elements = list(model.elements())
    assert beam_a not in elements
    assert beam_b not in elements


def test_remove_element_subtree_keeps_parent():
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(parent)

    assert parent in list(model.elements())


def test_remove_element_subtree_parent_has_no_children_after():
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(parent)

    assert parent.children == []


def test_remove_element_subtree_clears_cache_on_removed_elements():
    model, parent, beam_a, beam_b = _hierarchy_model()
    # Warm the cache first
    _ = beam_a.modeltransformation
    _ = beam_a.aabb

    model.remove_element_subtree(parent)

    assert beam_a._modeltransformation is None
    assert beam_a._aabb is None


def test_remove_element_subtree_removes_joints_spanning_only_descendants(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, parent, beam_a, beam_b = _hierarchy_model()
    joint = LButtJoint.create(model, beam_a, beam_b)
    assert len(list(model.joints)) == 1
    assert joint.location is not None
    model.remove_element_subtree(parent)

    assert len(list(model.joints)) == 0
    assert joint._location is None


def test_remove_element_subtree_leaf_element():
    """Calling on a leaf (no children) removes nothing — no-op."""
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.remove_element_subtree(beam_a)

    elements = list(model.elements())
    assert beam_a in elements
    assert parent in elements
    assert beam_b in elements


# ===========================================================================
# _detach_subtree / _attach_subtree round-trip
# ===========================================================================


def test_detach_subtree_no_parent_empties_model():
    model, parent, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree()

    assert len(list(model.elements())) == 0


def test_detach_subtree_with_parent_removes_only_children():
    model, parent, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree(parent)

    elements = list(model.elements())
    assert parent in elements
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
    model, parent, beam_a, beam_b = _hierarchy_model()

    tuples, joints = model._detach_subtree()

    # Tuple 0: (None, [parent]) — top-level
    # Tuple 1: (parent, [beam_a, beam_b]) — parent's children
    assert len(tuples) == 2
    parents = {t[0] for t in tuples}
    assert None in parents
    assert parent in parents


def test_detach_subtree_captures_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = _flat_model()
    joint = LButtJoint.create(model, b1, b2)

    tuples, joints = model._detach_subtree()

    assert joint in joints
    assert len(list(model.joints)) == 0


def test_attach_subtree_restores_elements():
    model, parent, beam_a, beam_b = _hierarchy_model()
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    elements = list(new_model.elements())
    assert parent in elements
    assert beam_a in elements
    assert beam_b in elements


def test_attach_subtree_restores_hierarchy():
    model, parent, beam_a, beam_b = _hierarchy_model()
    tuples, joints = model._detach_subtree()

    new_model = TimberModel()
    new_model._attach_subtree(tuples, joints=joints)

    assert beam_a in parent.children
    assert beam_b in parent.children


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
    root_parent = make_parent()
    target_model.add_element(root_parent)
    target_model._attach_subtree(tuples, parent=root_parent)

    assert b1 in root_parent.children
    assert b2 in root_parent.children


# ===========================================================================
# extract_model_from_parent
# ===========================================================================


def test_extract_model_from_parent_returns_new_model():
    model, parent, beam_a, beam_b = _hierarchy_model()

    extracted = model.extract_model_from_parent(parent)

    assert extracted is not model
    assert isinstance(extracted, TimberModel)


def test_extract_model_from_parent_new_model_contains_children():
    model, parent, beam_a, beam_b = _hierarchy_model()

    extracted = model.extract_model_from_parent(parent)

    elements = list(extracted.elements())
    assert beam_a in elements
    assert beam_b in elements


def test_extract_model_from_parent_parent_stays_in_original():
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.extract_model_from_parent(parent)

    assert parent in list(model.elements())


def test_extract_model_from_parent_children_leave_original():
    model, parent, beam_a, beam_b = _hierarchy_model()

    model.extract_model_from_parent(parent)

    elements = list(model.elements())
    assert beam_a not in elements
    assert beam_b not in elements


def test_extract_model_from_parent_preserves_hierarchy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model = TimberModel()
    parent = make_parent()
    beam_a = make_beam(x=0)
    beam_b = make_beam(x=2)
    inner_parent = make_parent()
    inner_beam = make_beam(x=4)
    model.add_element(parent)
    model.add_element(beam_a, parent=parent)
    model.add_element(beam_b, parent=parent)
    model.add_element(inner_parent, parent=beam_a)
    model.add_element(inner_beam, parent=inner_parent)

    _ = model.extract_model_from_parent(parent)

    assert inner_beam in inner_parent.children
    assert inner_parent in beam_a.children


def test_extract_model_from_parent_moves_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, parent, beam_a, beam_b = _hierarchy_model()
    joint = LButtJoint.create(model, beam_a, beam_b)

    extracted = model.extract_model_from_parent(parent)

    assert joint in extracted.joints
    assert len(list(model.joints)) == 0


# ===========================================================================
# merge_model
# ===========================================================================


def test_merge_model_moves_all_elements():
    source, parent, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    elements = list(target.elements())
    assert parent in elements
    assert beam_a in elements
    assert beam_b in elements


def test_merge_model_empties_source():
    source, parent, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    assert len(list(source.elements())) == 0


def test_merge_model_preserves_hierarchy():
    source, parent, beam_a, beam_b = _hierarchy_model()
    target = TimberModel()

    target.merge_model(source)

    assert beam_a in parent.children
    assert beam_b in parent.children


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
    root_parent = make_parent()
    target.add_element(root_parent)

    target.merge_model(source, parent=root_parent)

    assert b1 in root_parent.children
    assert b2 in root_parent.children


def test_merge_model_source_joints_cleared(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    source, b1, b2 = _flat_model()
    LButtJoint.create(source, b1, b2)
    target = TimberModel()

    target.merge_model(source)

    assert len(list(source.joints)) == 0
