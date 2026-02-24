import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import Joint
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


# =============================================================================
# Helpers / Fixtures
# =============================================================================


@pytest.fixture
def two_beam_model():
    """A model with two intersecting beams in an L-topology."""
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


@pytest.fixture
def three_beam_model():
    """A model with three beams for multi-joint scenarios."""
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    b3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    model.add_element(b1)
    model.add_element(b2)
    model.add_element(b3)
    return model, b1, b2, b3


@pytest.fixture
def crossing_beams_model():
    """Two beams that cross in space — suitable for connect_adjacent_beams."""
    model = TimberModel()
    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))
    b1 = Beam.from_centerline(line1, 0.1, 0.1)
    b2 = Beam.from_centerline(line2, 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


# =============================================================================
# Joint.create() returns Joint
# =============================================================================


def test_create_returns_joint_instance(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert isinstance(joint, Joint)
    assert isinstance(joint, LButtJoint)


def test_create_returns_correct_subclass(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = TButtJoint.create(model, b1, b2)
    assert type(joint) is TButtJoint


def test_created_joint_has_elements(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert b1 in joint.elements
    assert b2 in joint.elements


def test_created_joint_has_interactions(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert len(joint.interactions) >= 1
    for pair in joint.interactions:
        assert len(pair) == 2


def test_create_multiple_joints(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    j1 = LButtJoint.create(model, b1, b2)
    j2 = LButtJoint.create(model, b1, b3)
    assert isinstance(j1, Joint)
    assert isinstance(j2, Joint)
    assert j1 is not j2


# =============================================================================
# model.joints property
# =============================================================================


def test_joints_returns_set(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    joints = model.joints
    assert isinstance(joints, set)


def test_joints_empty_when_no_joints():
    model = TimberModel()
    assert len(model.joints) == 0
    assert isinstance(model.joints, set)


def test_joints_contains_joint_instances(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    for joint in model.joints:
        assert isinstance(joint, Joint)


def test_joints_count_matches_added(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    LButtJoint.create(model, b1, b2)
    LButtJoint.create(model, b1, b3)
    assert len(model.joints) == 2


def test_joints_preserves_type(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    joint = list(model.joints)[0]
    assert type(joint) is LButtJoint


def test_joints_with_different_types(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    LButtJoint.create(model, b1, b2)
    TButtJoint.create(model, b1, b3)
    types = {type(j) for j in model.joints}
    assert LButtJoint in types
    assert TButtJoint in types


# =============================================================================
# model.add_joint()
# =============================================================================


def test_add_joint_makes_it_retrievable(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint(b1, b2)
    model.add_joint(joint)
    assert joint in model.joints


def test_add_joint_creates_interaction_edge(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint(b1, b2)
    model.add_joint(joint)
    assert len(list(model.graph.edges())) >= 1


def test_added_joint_is_joint_instance(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint(b1, b2)
    model.add_joint(joint)
    retrieved = list(model.joints)[0]
    assert isinstance(retrieved, Joint)
    assert retrieved is joint


# =============================================================================
# model.remove_joint()
# =============================================================================


def test_remove_joint_removes_from_set(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert len(model.joints) == 1
    model.remove_joint(joint)
    assert len(model.joints) == 0


def test_remove_joint_preserves_elements(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    model.remove_joint(joint)
    assert b1 in model.beams
    assert b2 in model.beams


def test_remove_one_of_multiple_joints(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    j1 = LButtJoint.create(model, b1, b2)
    j2 = LButtJoint.create(model, b1, b3)
    model.remove_joint(j1)
    assert len(model.joints) == 1
    assert j2 in model.joints
    for j in model.joints:
        assert isinstance(j, Joint)


def test_remove_nonexistent_joint_no_error(two_beam_model):
    """Removing a joint that's not in the model should not raise."""
    model, b1, b2 = two_beam_model
    joint = LButtJoint(b1, b2)
    model.remove_joint(joint)  # should not raise


# =============================================================================
# model.get_interactions_for_element()
# =============================================================================


def test_get_interactions_returns_list(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    result = model.get_interactions_for_element(b1)
    assert isinstance(result, list)


def test_get_interactions_returns_joint_instances(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    interactions = model.get_interactions_for_element(b1)
    assert len(interactions) >= 1
    for item in interactions:
        assert isinstance(item, Joint)


def test_get_interactions_returns_correct_joint(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    interactions = model.get_interactions_for_element(b1)
    assert joint in interactions


def test_get_interactions_empty_for_unconnected_element():
    model = TimberModel()
    b = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    model.add_element(b)
    interactions = model.get_interactions_for_element(b)
    assert interactions == []


def test_get_interactions_multiple_joints(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    j1 = LButtJoint.create(model, b1, b2)
    j2 = LButtJoint.create(model, b1, b3)
    interactions = model.get_interactions_for_element(b1)
    assert len(interactions) == 2
    for item in interactions:
        assert isinstance(item, Joint)
    assert j1 in interactions
    assert j2 in interactions


def test_get_interactions_both_elements_see_joint(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    i1 = model.get_interactions_for_element(b1)
    i2 = model.get_interactions_for_element(b2)
    assert joint in i1
    assert joint in i2


# =============================================================================
# model.joint_candidates
# =============================================================================


def test_candidates_returns_set(crossing_beams_model):
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    candidates = model.joint_candidates
    assert isinstance(candidates, set)


def test_candidates_are_joint_subclass(crossing_beams_model):
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    for candidate in model.joint_candidates:
        assert isinstance(candidate, Joint)
        assert isinstance(candidate, JointCandidate)


def test_candidates_empty_when_none_added():
    model = TimberModel()
    assert len(model.joint_candidates) == 0


def test_manual_candidate_is_joint(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L)
    model.add_joint_candidate(candidate)
    retrieved = list(model.joint_candidates)[0]
    assert isinstance(retrieved, Joint)
    assert isinstance(retrieved, JointCandidate)
    assert retrieved is candidate


# =============================================================================
# Joint.promote_joint_candidate()
# =============================================================================


def test_promote_returns_joint(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L, location=Point(0, 0, 0))
    model.add_joint_candidate(candidate)
    joint = LButtJoint.promote_joint_candidate(model, candidate)
    assert isinstance(joint, Joint)
    assert isinstance(joint, LButtJoint)


def test_promote_adds_to_model_joints(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L, location=Point(0, 0, 0))
    model.add_joint_candidate(candidate)
    joint = LButtJoint.promote_joint_candidate(model, candidate)
    assert joint in model.joints


def test_promoted_joint_has_elements(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L, location=Point(0, 0, 0))
    model.add_joint_candidate(candidate)
    joint = LButtJoint.promote_joint_candidate(model, candidate)
    assert b1 in joint.elements
    assert b2 in joint.elements


def test_promoted_joint_inherits_topology(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L, location=Point(0, 0, 0))
    model.add_joint_candidate(candidate)
    joint = LButtJoint.promote_joint_candidate(model, candidate)
    assert joint.topology == JointTopology.TOPO_L


def test_promote_with_reordered_elements(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L, location=Point(0, 0, 0))
    model.add_joint_candidate(candidate)
    joint = LButtJoint.promote_joint_candidate(model, candidate, reordered_elements=[b2, b1])
    assert isinstance(joint, Joint)
    assert isinstance(joint, LButtJoint)


# =============================================================================
# Serialization roundtrip preserves Joint types
# =============================================================================


def test_joints_survive_serialization(two_beam_model, mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)

    restored = json_loads(json_dumps(model))
    assert len(restored.joints) == 1
    joint = list(restored.joints)[0]
    assert isinstance(joint, Joint)
    assert type(joint) is LButtJoint


def test_joint_type_preserved_after_serialization(three_beam_model, mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    mocker.patch("compas_timber.connections.TButtJoint.add_features")
    model, b1, b2, b3 = three_beam_model
    LButtJoint.create(model, b1, b2)
    TButtJoint.create(model, b1, b3)

    restored = json_loads(json_dumps(model))
    types = {type(j) for j in restored.joints}
    assert LButtJoint in types
    assert TButtJoint in types
    for j in restored.joints:
        assert isinstance(j, Joint)


def test_joint_elements_restored_after_serialization(two_beam_model, mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)

    restored = json_loads(json_dumps(model))
    joint = list(restored.joints)[0]
    assert len(joint.elements) == 2
    for elem in joint.elements:
        assert isinstance(elem, Beam)


def test_interactions_work_after_serialization(two_beam_model, mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)

    restored = json_loads(json_dumps(model))
    beam = restored.beams[0]
    interactions = restored.get_interactions_for_element(beam)
    assert len(interactions) >= 1
    for item in interactions:
        assert isinstance(item, Joint)


# =============================================================================
# process_joinery() works with Joint objects
# =============================================================================


def test_process_joinery_returns_list(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    errors = model.process_joinery()
    assert isinstance(errors, list)


def test_process_joinery_joints_remain_joint_instances(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    model.process_joinery()
    for j in model.joints:
        assert isinstance(j, Joint)


# =============================================================================
# Joint identity and consistency
# =============================================================================


def test_created_joint_is_same_object_in_model(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert joint in model.joints
    model_joint = [j for j in model.joints if j is joint]
    assert len(model_joint) == 1


def test_joint_guid_is_unique(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    j1 = LButtJoint.create(model, b1, b2)
    j2 = LButtJoint.create(model, b1, b3)
    assert str(j1.guid) != str(j2.guid)


def test_joint_has_name(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert joint.name is not None
    assert isinstance(joint.name, str)


def test_joint_str_representation(two_beam_model):
    model, b1, b2 = two_beam_model
    LButtJoint.create(model, b1, b2)
    model_str = str(model)
    assert "1 joint" in model_str


def test_model_str_with_no_joints():
    model = TimberModel()
    model_str = str(model)
    assert "0 joint" in model_str


# =============================================================================
# Edge cases
# =============================================================================


def test_candidates_and_joints_are_separate(crossing_beams_model):
    """Joint candidates should not appear in model.joints."""
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    assert len(model.joint_candidates) == 1
    assert len(model.joints) == 0


def test_adding_joint_does_not_affect_candidates(crossing_beams_model):
    """Adding a joint should not remove existing candidates."""
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    candidates_before = len(model.joint_candidates)
    LButtJoint.create(model, b1, b2)
    assert len(model.joint_candidates) == candidates_before
    assert len(model.joints) == 1


def test_joint_interactions_property(two_beam_model):
    """Joint.interactions returns list of tuples of elements."""
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    interactions = joint.interactions
    assert isinstance(interactions, list)
    assert len(interactions) >= 1
    for pair in interactions:
        assert isinstance(pair, tuple)
        assert all(isinstance(e, Beam) for e in pair)


def test_joint_elements_are_beams(two_beam_model):
    """Joint.elements should return Beam instances."""
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    for elem in joint.elements:
        assert isinstance(elem, Beam)
