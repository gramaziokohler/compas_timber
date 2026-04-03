from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import LButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def _make_two_beam_model(origin=None):
    """Helper: creates a TimberModel with two intersecting beams."""
    origin = origin or Point(0, 0, 0)
    model = TimberModel()
    b1 = Beam(Frame(origin, Vector(1, 0, 0), Vector(0, 1, 0)), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame(origin, Vector(0, 1, 0), Vector(0, 0, 1)), length=1.0, width=0.1, height=0.1)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


# =============================================================================
# Basic merge tests
# =============================================================================


def test_merge_model_elements_transferred():
    """Elements from the other model should appear in the target model."""
    model_a, a1, a2 = _make_two_beam_model()
    model_b, b1, b2 = _make_two_beam_model(Point(5, 0, 0))

    model_a.merge_model(model_b)

    assert len(model_a.beams) == 4
    assert a1 in model_a.beams
    assert a2 in model_a.beams
    assert b1 in model_a.beams
    assert b2 in model_a.beams


def test_merge_model_graph_nodes():
    """Graph should contain nodes for all elements after merge."""
    model_a, _, _ = _make_two_beam_model()
    model_b, _, _ = _make_two_beam_model(Point(5, 0, 0))

    model_a.merge_model(model_b)

    assert len(list(model_a.graph.nodes())) == 4


def test_merge_model_no_parent_under_root():
    """Without parent, merged elements should be top-level (under root)."""
    model_a = TimberModel()
    a1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    model_a.add_element(a1)

    model_b = TimberModel()
    b1 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    model_b.add_element(b1)

    model_a.merge_model(model_b)

    # b1's treenode parent should be the root
    root = model_a.tree.root
    child_elements = [child.element for child in root.children]
    assert a1 in child_elements
    assert b1 in child_elements


def test_merge_model_with_parent():
    """With parent specified, merged elements should be children of that parent."""
    model_a = TimberModel()
    parent_beam = Beam(Frame.worldXY(), length=2.0, width=0.2, height=0.2)
    model_a.add_element(parent_beam)

    model_b = TimberModel()
    child_beam = Beam(Frame.worldYZ(), length=0.5, width=0.05, height=0.05)
    model_b.add_element(child_beam)

    model_a.merge_model(model_b, parent=parent_beam)

    assert child_beam in model_a.beams
    assert child_beam.treenode.parent.element is parent_beam


# =============================================================================
# Interaction graph merge tests
# =============================================================================


def test_merge_model_interactions_as_island():
    """Interactions from the other model should appear as a disconnected island."""
    model_a, a1, a2 = _make_two_beam_model()
    model_a.add_interaction(a1, a2)

    model_b, b1, b2 = _make_two_beam_model(Point(5, 0, 0))
    model_b.add_interaction(b1, b2)

    model_a.merge_model(model_b)

    # Two separate edges, no cross-connections
    assert len(list(model_a.graph.edges())) == 2
    # b1 and b2 should be neighbors of each other
    b1_neighbors = list(model_a.graph.neighbors(b1.graphnode))
    assert b2.graphnode in b1_neighbors
    # a1 and b1 should NOT be neighbors
    a1_neighbors = list(model_a.graph.neighbors(a1.graphnode))
    assert b1.graphnode not in a1_neighbors
    assert b2.graphnode not in a1_neighbors


# =============================================================================
# Joint merge tests
# =============================================================================


def test_merge_model_with_joints(mocker):
    """Joints from the other model should be transferred to the target model."""
    mocker.patch("compas_timber.connections.LButtJoint.add_features")

    model_a, a1, a2 = _make_two_beam_model()
    joint_a = LButtJoint.create(model_a, a1, a2)

    model_b, b1, b2 = _make_two_beam_model(Point(5, 0, 0))
    joint_b = LButtJoint.create(model_b, b1, b2)

    model_a.merge_model(model_b)

    joints = list(model_a.joints)
    assert len(joints) == 2
    assert joint_a in joints
    assert joint_b in joints


def test_merge_model_joint_edge_attributes(mocker):
    """Joint GUID should be preserved on graph edges after merge."""
    mocker.patch("compas_timber.connections.LButtJoint.add_features")

    model_a, a1, a2 = _make_two_beam_model()
    LButtJoint.create(model_a, a1, a2)

    model_b, b1, b2 = _make_two_beam_model(Point(5, 0, 0))
    joint_b = LButtJoint.create(model_b, b1, b2)

    model_a.merge_model(model_b)

    # The edge between b1 and b2 should have the joint GUID
    joints_for_b1 = model_a.get_joints_for_element(b1)
    assert len(joints_for_b1) == 1
    assert joints_for_b1[0] is joint_b


# =============================================================================
# Joint candidate merge tests
# =============================================================================


def test_merge_model_with_candidates():
    """Joint candidates from the other model should be transferred."""
    model_a = TimberModel()
    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))
    a1 = Beam.from_centerline(line1, 0.1, 0.1)
    a2 = Beam.from_centerline(line2, 0.1, 0.1)
    model_a.add_element(a1)
    model_a.add_element(a2)
    model_a.connect_adjacent_beams()
    assert len(model_a.joint_candidates) == 1

    model_b = TimberModel()
    line3 = Line(Point(5, 0, 0), Point(6, 0, 0))
    line4 = Line(Point(5.5, -0.5, 0), Point(5.5, 0.5, 0))
    b1 = Beam.from_centerline(line3, 0.1, 0.1)
    b2 = Beam.from_centerline(line4, 0.1, 0.1)
    model_b.add_element(b1)
    model_b.add_element(b2)
    model_b.connect_adjacent_beams()
    assert len(model_b.joint_candidates) == 1

    model_a.merge_model(model_b)

    assert len(model_a.joint_candidates) == 2


# =============================================================================
# Tree hierarchy preservation tests
# =============================================================================


def test_merge_model_preserves_hierarchy():
    """Hierarchical parent-child relationships from the other model should be preserved."""
    model_a = TimberModel()
    a1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    model_a.add_element(a1)

    # model_b has parent-child hierarchy: group_beam -> child_beam
    model_b = TimberModel()
    group_beam = Beam(Frame.worldYZ(), length=2.0, width=0.2, height=0.2)
    child_beam = Beam(Frame(Point(1, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=0.5, width=0.05, height=0.05)
    model_b.add_element(group_beam)
    model_b.add_element(child_beam, parent=group_beam)

    model_a.merge_model(model_b)

    # child_beam should still be a child of group_beam
    assert child_beam.treenode.parent.element is group_beam
    # group_beam should be a top-level element (under root)
    assert group_beam.treenode.parent is model_a.tree.root
    assert len(model_a.beams) == 3


def test_merge_model_preserves_hierarchy_with_parent():
    """When parent is specified, top-level elements from other are children of parent, sub-hierarchy preserved."""
    model_a = TimberModel()
    parent_beam = Beam(Frame.worldXY(), length=2.0, width=0.2, height=0.2)
    model_a.add_element(parent_beam)

    model_b = TimberModel()
    group_beam = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    child_beam = Beam(Frame(Point(1, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=0.5, width=0.05, height=0.05)
    model_b.add_element(group_beam)
    model_b.add_element(child_beam, parent=group_beam)

    model_a.merge_model(model_b, parent=parent_beam)

    # group_beam should be a child of parent_beam
    assert group_beam.treenode.parent.element is parent_beam
    # child_beam should still be a child of group_beam
    assert child_beam.treenode.parent.element is group_beam


# =============================================================================
# Empty model merge tests
# =============================================================================


def test_merge_empty_model_into_populated():
    """Merging an empty model should be a no-op."""
    model_a, a1, a2 = _make_two_beam_model()
    model_b = TimberModel()

    model_a.merge_model(model_b)

    assert len(model_a.beams) == 2
    assert len(list(model_a.graph.nodes())) == 2


def test_merge_into_empty_model():
    """Merging into an empty model should transfer all elements."""
    model_a = TimberModel()
    model_b, b1, b2 = _make_two_beam_model()

    model_a.merge_model(model_b)

    assert len(model_a.beams) == 2
    assert b1 in model_a.beams
    assert b2 in model_a.beams


# =============================================================================
# Node attribute merge tests
# =============================================================================


def test_merge_model_node_attributes_preserved():
    """Node attributes (e.g. structural_segments) from the other model should be preserved."""
    from compas_timber.structural import StructuralSegment

    model_a = TimberModel()
    a1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    model_a.add_element(a1)

    model_b = TimberModel()
    b1 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    model_b.add_element(b1)

    # Add a structural segment to b1 in model_b
    segment = StructuralSegment(
        line=Line(Point(0, 0, 0), Point(0, 0, 1)),
        frame=Frame.worldXY(),
        cross_section=(0.1, 0.1),
    )
    model_b.add_beam_structural_segments(b1, [segment])

    model_a.merge_model(model_b)

    # Structural segment should be accessible on b1 via model_a
    segments = model_a.get_beam_structural_segments(b1)
    assert len(segments) == 1
    assert segments[0] is segment
