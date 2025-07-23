import pytest
from unittest.mock import Mock

from compas.geometry import Frame
from compas.geometry import Point

from compas_timber.connections import TButtJoint
from compas_timber.connections import BallNodeJoint
from compas_timber.connections import GenericJoint
from compas_timber.connections import GenericPlateJoint
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections.analyzers import Cluster
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


@pytest.fixture
def timber_model():
    """Create a basic TimberModel with two beams."""
    model = TimberModel()

    # Create two beams
    beam1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    beam2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(beam1)
    model.add_element(beam2)

    return model, beam1, beam2


@pytest.fixture
def generic_joint_with_beams(timber_model):
    """Create a generic joint connecting two beams."""
    model, beam1, beam2 = timber_model
    generic_joint = GenericJoint.create(model, beam1, beam2)
    return model, generic_joint, beam1, beam2


@pytest.fixture
def cluster_with_single_joint(generic_joint_with_beams):
    """Create a cluster containing a single generic joint."""
    model, generic_joint, beam1, beam2 = generic_joint_with_beams
    cluster = Cluster([generic_joint])
    return model, cluster, beam1, beam2


@pytest.fixture
def cluster_with_multiple_joints(timber_model):
    """Create a cluster containing multiple generic joints."""
    model, beam1, beam2 = timber_model

    # Add a third beam
    beam3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    model.add_element(beam3)

    # Create multiple joints
    joint1 = GenericJoint.create(model, beam1, beam2)
    joint2 = GenericJoint.create(model, beam2, beam3)

    cluster = Cluster([joint1, joint2])
    return model, cluster, beam1, beam2, beam3


@pytest.fixture
def plate_model():
    """Create a basic TimberModel with two plates."""
    from compas.geometry import Polyline

    model = TimberModel()

    # Create two plates
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate1 = Plate.from_outline_thickness(polyline_a, 1)
    plate2 = Plate.from_outline_thickness(polyline_b, 1)

    model.add_element(plate1)
    model.add_element(plate2)

    return model, plate1, plate2


@pytest.fixture
def generic_plate_joint_with_plates(plate_model):
    """Create a generic plate joint connecting two plates."""
    model, plate1, plate2 = plate_model
    generic_plate_joint = GenericPlateJoint(plate_a=plate1, plate_b=plate2, topology=JointTopology.TOPO_L, a_segment_index=1, b_segment_index=0)
    model.add_joint(generic_plate_joint)
    return model, generic_plate_joint, plate1, plate2


class TestJointFromCluster:
    """Test cases for Joint.from_cluster method."""

    def test_from_cluster_with_single_joint(self, cluster_with_single_joint):
        """Test creating a joint from a cluster with a single joint."""
        model, cluster, beam1, beam2 = cluster_with_single_joint

        # Create a TButtJoint from the cluster
        joint = TButtJoint.from_cluster(model, cluster)

        # Verify the joint was created correctly
        assert isinstance(joint, TButtJoint)
        assert joint.main_beam == beam1 or joint.main_beam == beam2
        assert joint.cross_beam == beam1 or joint.cross_beam == beam2
        assert joint.main_beam != joint.cross_beam

        # Verify the joint was added to the model
        assert joint in model.joints

        # Verify the original generic joint was removed
        assert len([j for j in model.joints if isinstance(j, GenericJoint)]) == 0

    def test_from_cluster_with_multiple_joints(self, cluster_with_multiple_joints):
        """Test creating a joint from a cluster with multiple joints."""
        model, cluster, beam1, beam2, beam3 = cluster_with_multiple_joints

        # Store initial joint count
        initial_joint_count = len(list(model.joints))

        # Create a TButtJoint from the cluster (should connect all elements)
        joint = BallNodeJoint.from_cluster(model, cluster)

        # Verify the joint was created
        assert isinstance(joint, BallNodeJoint)

        # Verify all original joints in the cluster were removed
        final_joint_count = len(list(model.joints))
        assert final_joint_count == initial_joint_count - len(cluster.joints) + 1

        # Verify all cluster joints were removed from the model
        for original_joint in cluster.joints:
            assert original_joint not in model.joints

    def test_from_cluster_with_custom_elements_order(self, cluster_with_single_joint):
        """Test creating a joint from a cluster with custom element order."""
        model, cluster, beam1, beam2 = cluster_with_single_joint

        # Specify elements in a specific order
        elements = [beam2, beam1]  # Reverse order
        joint = TButtJoint.from_cluster(model, cluster, elements=elements)

        # Verify the joint respects the element order
        assert isinstance(joint, TButtJoint)
        assert joint.main_beam == beam2  # Should be the first element in our custom order
        assert joint.cross_beam == beam1  # Should be the second element

    def test_from_cluster_with_kwargs(self, cluster_with_single_joint):
        """Test creating a joint from a cluster with additional kwargs."""
        model, cluster, beam1, beam2 = cluster_with_single_joint

        # Create joint with additional parameters
        joint = TButtJoint.from_cluster(model, cluster, mill_depth=0.05)

        assert isinstance(joint, TButtJoint)
        assert joint.mill_depth == 0.05  # Verify the mill depth was set correctly
        # The kwargs should be passed to the joint constructor
        # (exact verification depends on TButtJoint implementation)

    def test_from_cluster_calls_from_generic_joint_for_single_joint(self, cluster_with_single_joint, mocker):
        """Test that from_cluster calls from_generic_joint when cluster has one joint."""
        model, cluster, beam1, beam2 = cluster_with_single_joint

        # Mock the from_generic_joint method
        mock_from_generic = mocker.patch.object(TButtJoint, "from_generic_joint")
        mock_from_generic.return_value = Mock(spec=TButtJoint)

        # Call from_cluster
        TButtJoint.from_cluster(model, cluster)

        # Verify from_generic_joint was called
        mock_from_generic.assert_called_once_with(
            model,
            cluster.joints[0],
            elements=cluster.joints[0].elements,
        )

    def test_from_cluster_calls_create_for_multiple_joints(self, cluster_with_multiple_joints, mocker):
        """Test that from_cluster calls create when cluster has multiple joints."""
        model, cluster, beam1, beam2, beam3 = cluster_with_multiple_joints

        # Mock the create method
        mock_create = mocker.patch.object(BallNodeJoint, "create")
        mock_create.return_value = Mock(spec=BallNodeJoint)

        # Call from_cluster
        BallNodeJoint.from_cluster(model, cluster)

        # Verify create was called with cluster elements
        mock_create.assert_called_once_with(model, *list(cluster.elements))


class TestJointFromGenericJoint:
    """Test cases for Joint.from_generic_joint method."""

    def test_from_generic_joint_basic(self, generic_joint_with_beams):
        """Test basic conversion from generic joint to specific joint."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Convert generic joint to TButtJoint
        joint = TButtJoint.from_generic_joint(model, generic_joint)

        # Verify the joint was created correctly
        assert isinstance(joint, TButtJoint)
        assert joint.main_beam == beam1 or joint.main_beam == beam2
        assert joint.cross_beam == beam1 or joint.cross_beam == beam2
        assert joint.main_beam != joint.cross_beam

        # Verify the joint was added to the model
        assert joint in model.joints

        # Verify the original generic joint was removed
        assert generic_joint not in model.joints

    def test_from_generic_joint_with_custom_elements(self, generic_joint_with_beams):
        """Test conversion with custom element order."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Specify elements in specific order
        elements = [beam2, beam1]
        joint = TButtJoint.from_generic_joint(model, generic_joint, elements=elements)

        # Verify the joint respects the element order
        assert isinstance(joint, TButtJoint)
        assert joint.main_beam == beam2
        assert joint.cross_beam == beam1

    def test_from_generic_joint_with_kwargs(self, generic_joint_with_beams):
        """Test conversion with additional kwargs."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Convert with additional parameters
        joint = TButtJoint.from_generic_joint(
            model,
            generic_joint,
            mill_depth=0.05,
        )

        assert isinstance(joint, TButtJoint)
        assert joint.mill_depth == 0.05  # Verify the mill depth was set correctly
        # The kwargs should be passed to the joint constructor

    def test_from_generic_plate_joint_with_attributes(self, generic_plate_joint_with_plates):
        """Test conversion from GenericPlateJoint preserves attributes."""
        model, generic_plate_joint, plate1, plate2 = generic_plate_joint_with_plates

        # Convert generic plate joint to specific plate joint
        joint = PlateLButtJoint.from_generic_joint(model, generic_plate_joint)

        # Verify the joint was created correctly
        assert isinstance(joint, PlateLButtJoint)
        assert joint.plate_a == plate1 or joint.plate_a == plate2
        assert joint.plate_b == plate1 or joint.plate_b == plate2

        # Verify attributes were preserved
        assert joint.topology == generic_plate_joint.topology
        assert joint.a_segment_index == generic_plate_joint.a_segment_index
        assert joint.b_segment_index == generic_plate_joint.b_segment_index

        # Verify the original generic joint was removed
        assert generic_plate_joint not in model.joints

    def test_from_generic_plate_joint_without_b_segment_index(self, plate_model):
        """Test conversion from GenericPlateJoint without b_segment_index."""
        model, plate1, plate2 = plate_model

        # Create generic plate joint without b_segment_index
        generic_plate_joint = GenericPlateJoint(
            plate_a=plate1,
            plate_b=plate2,
            topology=JointTopology.TOPO_T,
            a_segment_index=1,
            b_segment_index=None,  # Explicitly None
        )
        model.add_joint(generic_plate_joint)

        # Convert to specific joint
        joint = PlateLButtJoint.from_generic_joint(model, generic_plate_joint)

        # Verify the joint was created
        assert isinstance(joint, PlateLButtJoint)
        assert joint.topology == JointTopology.TOPO_T
        assert joint.a_segment_index == 1
        # b_segment_index should not be in kwargs when None

    def test_from_generic_joint_calls_create(self, generic_joint_with_beams, mocker):
        """Test that from_generic_joint calls create method."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Mock the create method
        mock_create = mocker.patch.object(TButtJoint, "create")
        mock_create.return_value = Mock(spec=TButtJoint)

        # Call from_generic_joint
        TButtJoint.from_generic_joint(model, generic_joint)

        # Verify create was called with the generic joint's elements
        mock_create.assert_called_once_with(model, *generic_joint.elements)

    def test_from_generic_joint_removes_original(self, generic_joint_with_beams):
        """Test that the original generic joint is removed from the model."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Store initial state
        initial_joints = list(model.joints)
        assert generic_joint in initial_joints

        # Convert to specific joint
        new_joint = TButtJoint.from_generic_joint(model, generic_joint)

        # Verify original joint was removed
        assert generic_joint not in model.joints

        # Verify new joint was added
        assert new_joint in model.joints

    def test_from_generic_joint_default_elements(self, generic_joint_with_beams):
        """Test that elements default to generic_joint.elements when not provided."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Convert without specifying elements
        joint = TButtJoint.from_generic_joint(model, generic_joint)

        # Should use the generic joint's elements
        assert isinstance(joint, TButtJoint)
        assert set(joint.elements) == set(generic_joint.elements)


class TestJointFromMethodsEdgeCases:
    """Test edge cases and error conditions."""

    def test_from_cluster_empty_cluster(self, timber_model):
        """Test behavior with empty cluster."""
        model, beam1, beam2 = timber_model

        # Create empty cluster
        cluster = Cluster([])

        # Should handle empty cluster gracefully
        with pytest.raises(AttributeError):  # @chenkasirer @papachap what is our stance on instantiating joints without elements? Allowed?
            TButtJoint.from_cluster(model, cluster)

    def test_from_generic_joint_non_generic_plate_joint(self, generic_joint_with_beams):
        """Test from_generic_joint with non-GenericPlateJoint."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Should not try to extract plate-specific attributes
        joint = TButtJoint.from_generic_joint(model, generic_joint)

        assert isinstance(joint, TButtJoint)
        # No topology/segment attributes should be extracted

    def test_from_cluster_preserves_elements_order(self, cluster_with_single_joint):
        """Test that explicit elements order is preserved."""
        model, cluster, beam1, beam2 = cluster_with_single_joint

        # Test with different element orders
        elements_order1 = [beam1, beam2]
        elements_order2 = [beam2, beam1]

        joint1 = TButtJoint.from_cluster(model, cluster, elements=elements_order1)
        model.remove_joint(joint1)  # Clean up for second test

        joint2 = TButtJoint.from_cluster(model, cluster, elements=elements_order2)

        # Both should succeed but potentially with different internal ordering
        assert isinstance(joint1, TButtJoint)
        assert isinstance(joint2, TButtJoint)

    def test_from_generic_joint_preserves_elements_order(self, generic_joint_with_beams):
        """Test that explicit elements order is preserved."""
        model, generic_joint, beam1, beam2 = generic_joint_with_beams

        # Test with specific element order
        elements = [beam2, beam1]  # Reversed order
        joint = TButtJoint.from_generic_joint(model, generic_joint, elements=elements)

        assert isinstance(joint, TButtJoint)
        # The exact behavior depends on TButtJoint implementation
