import pytest
from unittest.mock import Mock

from compas.geometry import Point

from compas_timber.connections import PlateJointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections.solver import PlateSolverResult
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


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
    generic_plate_joint = PlateJointCandidate(plate_a=plate1, plate_b=plate2, topology=JointTopology.TOPO_L, a_segment_index=1, b_segment_index=0)
    model.add_joint(generic_plate_joint)
    return model, generic_plate_joint, plate1, plate2


def test_from_generic_plate_joint_with_attributes(generic_plate_joint_with_plates):
    """Test conversion from PlateJointCandidate preserves attributes."""
    model, generic_plate_joint, plate1, plate2 = generic_plate_joint_with_plates

    # Convert generic plate joint to specific plate joint
    joint = PlateLButtJoint.promote_joint_candidate(model, generic_plate_joint)

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


def test_from_generic_plate_joint_without_b_segment_index(plate_model):
    """Test conversion from PlateJointCandidate without b_segment_index."""
    model, plate1, plate2 = plate_model

    # Create generic plate joint without b_segment_index
    generic_plate_joint = PlateJointCandidate(
        plate_a=plate1,
        plate_b=plate2,
        topology=JointTopology.TOPO_T,
        a_segment_index=1,
        b_segment_index=None,  # Explicitly None
    )
    model.add_joint(generic_plate_joint)

    # Convert to specific joint
    joint = PlateLButtJoint.promote_joint_candidate(model, generic_plate_joint)

    # Verify the joint was created
    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_T
    assert joint.a_segment_index == 1
    # b_segment_index should not be in kwargs when None


def test_plate_joint_from_generic_joint_topology_solver_not_called_when_attributes_set(plate_model, mocker):
    """Test that PlateConnectionSolver.find_topology is NOT called when PlateJointCandidate already has topology and segment indices set."""
    from compas_timber.connections.solver import PlateConnectionSolver

    model, plate1, plate2 = plate_model

    # Create generic plate joint with all required attributes already set
    generic_plate_joint = PlateJointCandidate(plate_a=plate1, plate_b=plate2, topology=JointTopology.TOPO_EDGE_EDGE, a_segment_index=1, b_segment_index=0)
    model.add_joint(generic_plate_joint)

    # Mock the PlateConnectionSolver.find_topology method
    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")

    # Convert generic plate joint to specific plate joint
    joint = PlateLButtJoint.promote_joint_candidate(model, generic_plate_joint)

    # Verify the joint was created correctly
    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE
    assert joint.a_segment_index == 1
    assert joint.b_segment_index == 0

    # Verify that find_topology was NOT called since all attributes were already set
    mock_find_topology.assert_not_called()

    # Verify the original generic joint was removed
    assert generic_plate_joint not in model.joints


def test_plate_joint_from_generic_joint_topology_solver_called_when_attributes_missing(plate_model, mocker):
    """Test that PlateConnectionSolver.find_topology IS called when PlateJointCandidate has missing segment indices."""
    from compas_timber.connections.solver import PlateConnectionSolver

    model, plate1, plate2 = plate_model

    # Mock the PlateConnectionSolver.find_topology method to return expected results
    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")
    mock_find_topology.return_value = PlateSolverResult(topology=JointTopology.TOPO_EDGE_EDGE, plate_a=plate1, plate_b=plate2, a_segment_index=1, b_segment_index=0)

    # Convert generic plate joint to specific plate joint
    joint = PlateLButtJoint.create(model, plate1, plate2)

    # Verify the joint was created correctly
    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE

    # Verify that find_topology WAS called since a_segment_index was None
    mock_find_topology.assert_called_once_with(plate1, plate2)
