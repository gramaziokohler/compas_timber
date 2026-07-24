import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import Joint
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
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
def miter_beam_pair():
    """Two beams meeting at a right angle at the origin, suitable for a real LMiterJoint.

    LMiterJoint extends and adds features to *both* of its beams, unlike e.g. ButtJoint
    (which only extends its main_beam). That symmetry is needed here so that
    joint.clear_extensions()/clear_features() have something to clear on every element,
    which is what the removal-related tests below exercise.
    """
    model = TimberModel()
    b1 = Beam(frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=30.0, height=30.0, length=200.0)
    b2 = Beam(frame=Frame(Point(0, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30.0, height=30.0, length=200.0)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


@pytest.fixture
def miter_beam_triplet():
    """Three beams meeting at the origin, for multi-joint add_joint()/remove_element() scenarios."""
    model = TimberModel()
    b1 = Beam(frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=30.0, height=30.0, length=200.0)
    b2 = Beam(frame=Frame(Point(0, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30.0, height=30.0, length=200.0)
    b3 = Beam(frame=Frame(Point(0, 0, 0), Vector(0, 0, 1), Vector(1, 0, 0)), width=30.0, height=30.0, length=200.0)
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


def test_joints_empty_when_no_joints():
    model = TimberModel()
    assert len(model.joints) == 0


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


def test_add_joint_removes_old_joint_between_same_elements(miter_beam_pair):
    """Adding a new joint over an existing element pair should drop the old joint."""
    model, b1, b2 = miter_beam_pair
    old_joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()

    new_joint = LMiterJoint.create(model, b1, b2, cutoff=True)

    assert old_joint not in model.joints
    assert new_joint in model.joints
    assert len(model.joints) == 1


def test_add_joint_clears_old_joints_features_from_elements(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    old_joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()
    old_features = list(old_joint.features)
    assert old_features, "sanity check: old joint should have produced features"

    LMiterJoint.create(model, b1, b2, cutoff=True)

    for feature in old_features:
        assert feature not in b1.features
        assert feature not in b2.features


def test_add_joint_clears_old_joints_extensions_from_elements(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    old_joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()
    assert old_joint.guid in b1._blank_extensions
    assert old_joint.guid in b2._blank_extensions

    LMiterJoint.create(model, b1, b2, cutoff=True)

    assert old_joint.guid not in b1._blank_extensions
    assert old_joint.guid not in b2._blank_extensions


def test_add_joint_keeps_joints_on_unrelated_elements(miter_beam_triplet):
    """Replacing the joint on one element pair shouldn't disturb a joint on a different pair."""
    model, b1, b2, b3 = miter_beam_triplet
    LMiterJoint.create(model, b1, b2)
    other_joint = LMiterJoint.create(model, b2, b3)
    model.process_joinery()

    LMiterJoint.create(model, b1, b2, cutoff=True)

    assert other_joint in model.joints
    assert len(model.joints) == 2


# =============================================================================
# model.get_joint()
# =============================================================================


def test_get_joint_returns_the_joint_between_two_elements(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert model.get_joint(b1, b2) is joint


def test_get_joint_is_order_independent(two_beam_model):
    model, b1, b2 = two_beam_model
    joint = LButtJoint.create(model, b1, b2)
    assert model.get_joint(b2, b1) is joint


def test_get_joint_returns_none_when_elements_not_joined(three_beam_model):
    model, b1, b2, b3 = three_beam_model
    LButtJoint.create(model, b1, b2)
    assert model.get_joint(b1, b3) is None


def test_get_joint_returns_none_for_elements_without_any_joint(two_beam_model):
    model, b1, b2 = two_beam_model
    assert model.get_joint(b1, b2) is None


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
# model.remove_element() removes joints connected to the removed element
# =============================================================================


def test_remove_element_removes_joint_from_model(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()

    model.remove_element(b1)

    assert joint not in model.joints
    assert len(model.joints) == 0


def test_remove_element_keeps_joints_on_unrelated_elements(miter_beam_triplet):
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)
    model.process_joinery()

    model.remove_element(b1)

    assert j1 not in model.joints
    assert j2 in model.joints
    assert len(model.joints) == 1


def test_remove_element_clears_joint_features_from_surviving_element(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()
    features_before = list(joint.features)
    assert features_before, "sanity check: joint should have produced features"
    assert b2.features, "sanity check: surviving beam should carry joint features"

    model.remove_element(b1)

    for feature in features_before:
        assert feature not in b2.features


def test_remove_element_clears_joint_extensions_from_surviving_element(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    joint = LMiterJoint.create(model, b1, b2)
    model.process_joinery()
    assert joint.guid in b2._blank_extensions

    model.remove_element(b1)

    assert joint.guid not in b2._blank_extensions


def test_remove_element_removes_the_element_itself(miter_beam_pair):
    model, b1, b2 = miter_beam_pair
    LMiterJoint.create(model, b1, b2)
    model.process_joinery()

    model.remove_element(b1)

    assert b1 not in model.beams
    assert b2 in model.beams


def test_remove_element_of_unconnected_element_no_error():
    """Removing an element with no joints should behave like the base Model.remove_element()."""
    model = TimberModel()
    b = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    model.add_element(b)

    model.remove_element(b)

    assert b not in model.beams


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
    _ = LButtJoint.create(model, b1, b2)
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


def test_candidates_are_joint_candidate_instances(crossing_beams_model):
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    for candidate in model.joint_candidates:
        assert isinstance(candidate, JointCandidate)


def test_candidates_empty_when_none_added():
    model = TimberModel()
    assert len(model.joint_candidates) == 0


def test_manual_candidate_is_joint_candidate(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L)
    model.add_joint_candidate(candidate)
    retrieved = list(model.joint_candidates)[0]
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
# process_joinery(joints_to_process=...)
# =============================================================================


def test_process_joinery_default_processes_all_model_joints(miter_beam_triplet):
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)

    errors = model.process_joinery()

    assert errors == []
    assert j1.features, "joint not passed via joints_to_process should still be processed by default"
    assert j2.features
    assert j1.guid in b1._blank_extensions
    assert j2.guid in b3._blank_extensions


def test_process_joinery_with_subset_processes_only_given_joints(miter_beam_triplet):
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)

    errors = model.process_joinery(joints_to_process=[j1])

    assert errors == []
    assert j1.features, "j1 was passed via joints_to_process and should have been processed"
    assert j1.guid in b1._blank_extensions
    assert j1.guid in b2._blank_extensions
    assert j2.features == [], "j2 was not passed via joints_to_process and should be untouched"
    assert j2.guid not in b2._blank_extensions
    assert j2.guid not in b3._blank_extensions


def test_process_joinery_with_empty_list_processes_nothing(miter_beam_triplet):
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)

    errors = model.process_joinery(joints_to_process=[])

    assert errors == []
    assert j1.features == []
    assert j2.features == []
    assert not b1._blank_extensions
    assert not b2._blank_extensions
    assert not b3._blank_extensions


def test_process_joinery_subset_reprocessing_does_not_duplicate_features(miter_beam_triplet):
    """Calling process_joinery() again with the same subset should clear and recompute, not accumulate."""
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    LMiterJoint.create(model, b2, b3)

    model.process_joinery(joints_to_process=[j1])
    feature_count_after_first_pass = len(j1.features)
    b1_feature_count_after_first_pass = len(b1.features)

    model.process_joinery(joints_to_process=[j1])

    assert len(j1.features) == feature_count_after_first_pass
    assert len(b1.features) == b1_feature_count_after_first_pass


def test_process_joinery_subset_does_not_clear_features_of_excluded_joints(miter_beam_triplet):
    """Joints outside joints_to_process should keep whatever features they already had."""
    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)
    model.process_joinery()
    j2_features_before = list(j2.features)
    assert j2_features_before, "sanity check: j2 should have features from the full process_joinery() run"

    model.process_joinery(joints_to_process=[j1])

    assert j2.features == j2_features_before
    # each feature lands on one side of the joint or the other, not both
    remaining_features = list(b2.features) + list(b3.features)
    for feature in j2_features_before:
        assert feature in remaining_features


def test_process_joinery_returns_errors_only_for_processed_joints(miter_beam_triplet, mocker):
    from compas_timber.errors import BeamJoiningError

    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)
    mocker.patch.object(j2, "add_extensions", side_effect=BeamJoiningError(j2.elements, j2, debug_info="boom"))

    errors_without_j2 = model.process_joinery(joints_to_process=[j1])
    assert errors_without_j2 == []

    errors_with_j2 = model.process_joinery(joints_to_process=[j1, j2])
    assert len(errors_with_j2) == 1
    assert errors_with_j2[0].joint is j2


def test_process_joinery_stop_on_first_error_respects_subset(miter_beam_triplet, mocker):
    from compas_timber.errors import BeamJoiningError

    model, b1, b2, b3 = miter_beam_triplet
    j1 = LMiterJoint.create(model, b1, b2)
    j2 = LMiterJoint.create(model, b2, b3)
    mocker.patch.object(j2, "add_extensions", side_effect=BeamJoiningError(j2.elements, j2, debug_info="boom"))

    # j2 excluded from the subset: its error is never triggered, so nothing to raise
    model.process_joinery(joints_to_process=[j1], stop_on_first_error=True)

    # j2 included: its error should now propagate
    with pytest.raises(BeamJoiningError):
        model.process_joinery(joints_to_process=[j1, j2], stop_on_first_error=True)


# =============================================================================
# process_joinery() is idempotent
# =============================================================================


def test_process_joinery_repeated_full_run_is_idempotent(miter_beam_triplet):
    """Running process_joinery() more than once must not change the resulting extensions or feature counts.

    Beam.add_blank_extension() accumulates onto any existing entry for the same joint guid, so without
    clearing extensions before recomputing them, a second process_joinery() call would silently double
    the extension amount on every re-run. This asserts the exact (start, end) values, not just presence,
    so that kind of drift would be caught.
    """
    model, b1, b2, b3 = miter_beam_triplet
    LMiterJoint.create(model, b1, b2)
    LMiterJoint.create(model, b2, b3)

    model.process_joinery()
    extensions_after_first_run = {b: dict(b._blank_extensions) for b in (b1, b2, b3)}
    feature_counts_after_first_run = {b: len(b.features) for b in (b1, b2, b3)}
    assert any(extensions_after_first_run[b] for b in (b1, b2, b3)), "sanity check: something should have been extended"

    model.process_joinery()
    model.process_joinery()  # a third time, for good measure

    for b in (b1, b2, b3):
        assert b._blank_extensions == extensions_after_first_run[b]
        assert len(b.features) == feature_counts_after_first_run[b]


def test_process_joinery_repeated_subset_run_is_idempotent(miter_beam_pair):
    """Same as above, but for the joints_to_process subset path specifically."""
    model, b1, b2 = miter_beam_pair
    joint = LMiterJoint.create(model, b1, b2)

    model.process_joinery(joints_to_process=[joint])
    extensions_after_first_run = dict(b1._blank_extensions)
    feature_count_after_first_run = len(b1.features)
    assert extensions_after_first_run, "sanity check: something should have been extended"

    model.process_joinery(joints_to_process=[joint])
    model.process_joinery(joints_to_process=[joint])

    assert b1._blank_extensions == extensions_after_first_run
    assert len(b1.features) == feature_count_after_first_run


def test_process_joinery_subset_result_matches_full_run_result():
    """Processing a joint through joints_to_process must produce the same result as a full process_joinery() run.

    Two independent, geometrically identical models: one processes its single joint through the
    joints_to_process subset path, the other through the default full-model path. The resulting
    extension amounts and feature counts must match -- which path a joint is processed through
    shouldn't change what it computes.
    """
    model_subset = TimberModel()
    s1 = Beam(frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=30.0, height=30.0, length=200.0)
    s2 = Beam(frame=Frame(Point(0, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30.0, height=30.0, length=200.0)
    model_subset.add_element(s1)
    model_subset.add_element(s2)
    joint_subset = LMiterJoint.create(model_subset, s1, s2)
    model_subset.process_joinery(joints_to_process=[joint_subset])

    model_full = TimberModel()
    f1 = Beam(frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=30.0, height=30.0, length=200.0)
    f2 = Beam(frame=Frame(Point(0, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30.0, height=30.0, length=200.0)
    model_full.add_element(f1)
    model_full.add_element(f2)
    LMiterJoint.create(model_full, f1, f2)
    model_full.process_joinery()

    assert set(s1._blank_extensions.values()) == set(f1._blank_extensions.values())
    assert len(s1.features) == len(f1.features)


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
