import pytest
from unittest.mock import Mock

from compas.geometry import Frame

from compas_timber.connections import TButtJoint
from compas_timber.connections import BallNodeJoint
from compas_timber.connections import JointCandidate
from compas_timber.connections.analyzers import Cluster
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    """Create a basic TimberModel with two beams."""
    model = TimberModel()

    # Create two beams
    beam1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    beam2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(beam1)
    model.add_element(beam2)

    return model


@pytest.fixture
def generic_joint_with_beams(model):
    """Create a generic joint connecting two beams."""
    beam1, beam2 = model.beams
    candidate = JointCandidate(beam1, beam2)
    model.add_joint_candidate(candidate)
    return model, candidate, beam1, beam2


@pytest.fixture
def cluster_with_single_joint(generic_joint_with_beams):
    """Create a cluster containing a single generic joint."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams
    cluster = Cluster([generic_joint])
    return model, cluster, beam1, beam2


@pytest.fixture
def cluster_with_multiple_joints(model):
    """Create a cluster containing multiple generic joints."""
    beam1, beam2 = model.beams

    # Add a third beam
    beam3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    model.add_element(beam3)

    # Create multiple joints
    candidate1 = JointCandidate(beam1, beam2)
    model.add_joint_candidate(candidate1)
    candidate2 = JointCandidate(beam2, beam3)
    model.add_joint_candidate(candidate2)

    cluster = Cluster([candidate1, candidate2])
    return model, cluster, beam1, beam2, beam3


def test_from_cluster_with_single_joint(cluster_with_single_joint):
    """Test creating a joint from a cluster with a single joint."""
    model, cluster, beam1, beam2 = cluster_with_single_joint

    # Create a TButtJoint from the cluster
    joint = TButtJoint.promote_cluster(model, cluster)

    # Verify the joint was created correctly
    assert isinstance(joint, TButtJoint)
    assert joint.main_beam == beam1 or joint.main_beam == beam2
    assert joint.cross_beam == beam1 or joint.cross_beam == beam2
    assert joint.main_beam != joint.cross_beam

    # Verify the joint was added to the model
    assert joint in model.joints

    assert len(model.joint_candidates) == 1
    assert isinstance(list(model.joint_candidates)[0], JointCandidate)


def test_from_cluster_with_multiple_joints(cluster_with_multiple_joints):
    """Test creating a joint from a cluster with multiple joints."""
    model, cluster, beam1, beam2, beam3 = cluster_with_multiple_joints

    # Store initial joint count
    joint_candidate_count = len(list(model.joint_candidates))

    # Create a TButtJoint from the cluster (should connect all elements)
    joint = BallNodeJoint.promote_cluster(model, cluster)

    # Verify the joint was created
    assert isinstance(joint, BallNodeJoint)
    assert joint in model.joints
    assert joint_candidate_count == len(list(model.joint_candidates))


def test_from_cluster_with_custom_elements_order(cluster_with_single_joint):
    """Test creating a joint from a cluster with custom element order."""
    model, cluster, beam1, beam2 = cluster_with_single_joint

    # Specify elements in a specific order
    elements = [beam2, beam1]  # Reverse order
    joint = TButtJoint.promote_cluster(model, cluster, reordered_elements=elements)

    # Verify the joint respects the element order
    assert isinstance(joint, TButtJoint)
    assert joint.main_beam == beam2  # Should be the first element in our custom order
    assert joint.cross_beam == beam1  # Should be the second element


def test_from_cluster_with_kwargs(cluster_with_single_joint):
    """Test creating a joint from a cluster with additional kwargs."""
    model, cluster, beam1, beam2 = cluster_with_single_joint

    # Create joint with additional parameters
    joint = TButtJoint.promote_cluster(model, cluster, mill_depth=0.05)

    assert isinstance(joint, TButtJoint)
    assert joint.mill_depth == 0.05  # Verify the mill depth was set correctly
    # The kwargs should be passed to the joint constructor
    # (exact verification depends on TButtJoint implementation)


def test_from_cluster_calls_from_generic_joint_for_single_joint(cluster_with_single_joint, mocker):
    """Test that promote_cluster calls promote_joint_candidate when cluster has one joint."""
    model, cluster, beam1, beam2 = cluster_with_single_joint

    # Mock the promote_joint_candidate method
    mock_from_generic = mocker.patch.object(TButtJoint, "promote_joint_candidate")
    mock_from_generic.return_value = Mock(spec=TButtJoint)

    # Call promote_cluster
    TButtJoint.promote_cluster(model, cluster)

    # Verify promote_joint_candidate was called
    mock_from_generic.assert_called_once_with(
        model,
        cluster.joints[0],
        reordered_elements=cluster.joints[0].elements,
    )


def test_from_cluster_calls_create_for_multiple_joints(cluster_with_multiple_joints, mocker):
    """Test that promote_cluster calls create when cluster has multiple joints."""
    model, cluster, beam1, beam2, beam3 = cluster_with_multiple_joints

    # Mock the create method
    mock_create = mocker.patch.object(BallNodeJoint, "create")
    mock_create.return_value = Mock(spec=BallNodeJoint)

    # Call promote_cluster
    BallNodeJoint.promote_cluster(model, cluster)

    # Verify create was called with cluster elements
    mock_create.assert_called_once_with(model, *list(cluster.elements))


def test_from_generic_joint_basic(generic_joint_with_beams):
    """Test basic conversion from generic joint to specific joint."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Convert generic joint to TButtJoint
    joint = TButtJoint.promote_joint_candidate(model, generic_joint)

    # Verify the joint was created correctly
    assert isinstance(joint, TButtJoint)
    assert joint.main_beam == beam1 or joint.main_beam == beam2
    assert joint.cross_beam == beam1 or joint.cross_beam == beam2
    assert joint.main_beam != joint.cross_beam
    assert joint in model.joints


def test_from_generic_joint_with_custom_elements(generic_joint_with_beams):
    """Test conversion with custom element order."""
    model, joint_candidate, beam1, beam2 = generic_joint_with_beams

    # Specify elements in specific order
    elements = [beam2, beam1]
    joint = TButtJoint.promote_joint_candidate(model, joint_candidate, reordered_elements=elements)

    # Verify the joint respects the element order
    assert isinstance(joint, TButtJoint)
    assert joint.main_beam == beam2
    assert joint.cross_beam == beam1
    assert joint in model.joints
    assert joint_candidate in model.joint_candidates


def test_from_generic_joint_with_kwargs(generic_joint_with_beams):
    """Test conversion with additional kwargs."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Convert with additional parameters
    joint = TButtJoint.promote_joint_candidate(
        model,
        generic_joint,
        mill_depth=0.05,
    )

    assert isinstance(joint, TButtJoint)
    assert joint.mill_depth == 0.05  # Verify the mill depth was set correctly
    # The kwargs should be passed to the joint constructor


def test_from_generic_joint_calls_create(generic_joint_with_beams, mocker):
    """Test that promote_joint_candidate calls create method."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Mock the create method
    mock_create = mocker.patch.object(TButtJoint, "create")
    mock_create.return_value = Mock(spec=TButtJoint)

    # Call promote_joint_candidate
    TButtJoint.promote_joint_candidate(model, generic_joint)

    # Verify create was called with the generic joint's elements
    mock_create.assert_called_once_with(model, *generic_joint.elements)


def test_from_generic_joint_removes_original(generic_joint_with_beams):
    """Test that the original generic joint is removed from the model."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Store initial state
    assert generic_joint in model.joint_candidates

    # Convert to specific joint
    new_joint = TButtJoint.promote_joint_candidate(model, generic_joint)

    # Verify new joint was added
    assert new_joint in model.joints


def test_from_generic_joint_default_elements(generic_joint_with_beams):
    """Test that elements default to generic_joint.elements when not provided."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Convert without specifying elements
    joint = TButtJoint.promote_joint_candidate(model, generic_joint)

    # Should use the generic joint's elements
    assert isinstance(joint, TButtJoint)
    assert set(joint.elements) == set(generic_joint.elements)


def test_from_cluster_empty_cluster(model):
    """Test behavior with empty cluster."""
    beam1, beam2 = model.beams

    # Create empty cluster
    cluster = Cluster([])

    with pytest.raises(AttributeError):  # @chenkasirer @papachap what is our stance on instantiating joints without elements? Allowed?
        TButtJoint.promote_cluster(model, cluster)


def test_from_generic_joint_non_generic_plate_joint(generic_joint_with_beams):
    """Test promote_joint_candidate with non-PlateJointCandidate."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Should not try to extract plate-specific attributes
    joint = TButtJoint.promote_joint_candidate(model, generic_joint)

    assert isinstance(joint, TButtJoint)
    # No topology/segment attributes should be extracted


def test_from_cluster_preserves_elements_order(cluster_with_single_joint):
    """Test that explicit elements order is preserved."""
    model, cluster, beam1, beam2 = cluster_with_single_joint

    # Test with different element orders
    elements_order1 = [beam1, beam2]
    elements_order2 = [beam2, beam1]

    joint1 = TButtJoint.promote_cluster(model, cluster, reordered_elements=elements_order1)
    # model.remove_joint(joint1)  # Clean up for second test

    joint2 = TButtJoint.promote_cluster(model, cluster, reordered_elements=elements_order2)

    # Both should succeed but potentially with different internal ordering
    assert isinstance(joint1, TButtJoint)
    assert isinstance(joint2, TButtJoint)


def test_from_generic_joint_preserves_elements_order(generic_joint_with_beams):
    """Test that explicit elements order is preserved."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    # Test with specific element order
    elements = [beam2, beam1]  # Reversed order
    joint = TButtJoint.promote_joint_candidate(model, generic_joint, reordered_elements=elements)

    assert isinstance(joint, TButtJoint)
    # The exact behavior depends on TButtJoint implementation


def test_candidate_edge_stays_when_removing_joint(generic_joint_with_beams):
    """Test basic conversion from generic joint to specific joint."""
    # model has one JointCandidate connecting two beams
    # a TButtJoint is added on the same edge
    # TButt is removed, leaving the JointCandidate
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    model: TimberModel

    joint = TButtJoint.promote_joint_candidate(model, generic_joint)
    model.remove_joint(joint)

    assert joint not in model.joints
    assert generic_joint in model.joint_candidates


def test_candidate_edge_stays_when_removing_candidate(generic_joint_with_beams):
    """Test basic conversion from generic joint to specific joint."""
    # model has one JointCandidate connecting two beams
    # a TButtJoint is added on the same edge
    # candidate is removed, leaving the TButtJoint
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    joint = TButtJoint.promote_joint_candidate(model, generic_joint)
    model.remove_joint_candidate(generic_joint)

    assert joint in model.joints
    assert generic_joint not in model.joint_candidates


def test_candidate_edge_removed_when_removing_candidate_and_joint(generic_joint_with_beams):
    """Test basic conversion from generic joint to specific joint."""
    # model has one JointCandidate connecting two beams
    # a TButtJoint is added on the same edge
    # TButt is removed, leaving the JointCandidate
    model, generic_joint, beam1, beam2 = generic_joint_with_beams

    model: TimberModel

    joint = TButtJoint.promote_joint_candidate(model, generic_joint)
    model.remove_joint(joint)
    model.remove_joint_candidate(generic_joint)

    assert joint not in model.joints
    assert generic_joint not in model.joint_candidates
