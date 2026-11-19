import pytest

from compas.geometry import Point

from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections import PlateTopologyInfo
from compas_timber.connections import TopologyInfo
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


@pytest.fixture
def model():
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

    return model


def _plate_topology_info(plate1, plate2, topology, a_segment_index, b_segment_index, location=None):
    """A hand-built TopologyInfo (no solver involved) with the given per-plate edge indices."""
    return TopologyInfo(
        topology,
        distance=0.0,
        location=location or Point(5, 10, 0),
        element_topo_info={
            str(plate1.guid): PlateTopologyInfo(role="edge", edge_index=a_segment_index),
            str(plate2.guid): PlateTopologyInfo(role="edge", edge_index=b_segment_index),
        },
    )


@pytest.fixture
def candidate_with_plates(model):
    """Create a joint candidate connecting two plates."""
    plate1, plate2 = model.plates
    topology_info = _plate_topology_info(plate1, plate2, JointTopology.TOPO_L, 1, 0)
    candidate = JointCandidate(plate1, plate2, topology_info=topology_info)
    model.add_joint_candidate(candidate)
    return model, candidate, plate1, plate2


def test_promote_candidate_preserves_attributes(candidate_with_plates):
    """Promoting a candidate passes topology, location, distance and per-plate segment indices to the joint."""
    model, candidate, plate1, plate2 = candidate_with_plates

    joint = PlateLButtJoint.promote_joint_candidate(model, candidate)

    assert isinstance(joint, PlateLButtJoint)
    assert joint.plate_a is plate1
    assert joint.plate_b is plate2
    assert joint.topology == candidate.topology
    assert joint.location == candidate.location
    assert joint.distance == candidate.distance
    assert joint.a_segment_index == candidate.info_for(plate1).edge_index == 1
    assert joint.b_segment_index == candidate.info_for(plate2).edge_index == 0
    assert candidate not in model.joints


def test_promote_candidate_reordered_elements_segment_indices_follow_plates(candidate_with_plates):
    """Segment indices are looked up per plate, so reordering the plates on promotion swaps them accordingly."""
    model, candidate, plate1, plate2 = candidate_with_plates

    joint = PlateLButtJoint.promote_joint_candidate(model, candidate, reordered_elements=[plate2, plate1])

    assert joint.plate_a is plate2
    assert joint.plate_b is plate1
    assert joint.a_segment_index == 0
    assert joint.b_segment_index == 1


def test_promote_candidate_without_b_segment_index(model):
    """Promotion works when only one plate has a segment index."""
    plate1, plate2 = model.plates
    topology_info = _plate_topology_info(plate1, plate2, JointTopology.TOPO_T, 1, None)
    candidate = JointCandidate(plate1, plate2, topology_info=topology_info)
    model.add_joint_candidate(candidate)

    joint = PlateLButtJoint.promote_joint_candidate(model, candidate)

    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_T
    assert joint.a_segment_index == 1
    assert joint.b_segment_index is None


def test_promote_solved_candidate_matches_solver(model):
    """A candidate without topology info is solved lazily; promoting it gives the solver's values."""
    plate1, plate2 = model.plates
    solved = PlateConnectionSolver().find_topology(plate1, plate2, max_distance=None)
    plate_a, plate_b = solved.get_element_by_role(plate1, plate2)
    candidate = JointCandidate(plate_a, plate_b)
    model.add_joint_candidate(candidate)

    joint = PlateLButtJoint.promote_joint_candidate(model, candidate)

    assert joint.topology == solved.topology
    assert joint.location == solved.location
    assert joint.distance == solved.distance
    assert joint.a_segment_index == solved.info_for(plate_a).edge_index
    assert joint.b_segment_index == solved.info_for(plate_b).edge_index


def test_plate_joint_from_candidate_topology_solver_not_called_when_attributes_set(model, mocker):
    """PlateConnectionSolver.find_topology is NOT called when the candidate already has its topology info."""
    plate1, plate2 = model.plates
    topology_info = _plate_topology_info(plate1, plate2, JointTopology.TOPO_EDGE_EDGE, 1, 0)
    candidate = JointCandidate(plate1, plate2, topology_info=topology_info)
    model.add_joint_candidate(candidate)

    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")

    joint = PlateLButtJoint.promote_joint_candidate(model, candidate)

    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE
    assert joint.a_segment_index == 1
    assert joint.b_segment_index == 0
    mock_find_topology.assert_not_called()
    assert candidate not in model.joints


def test_plate_joint_topology_solver_called_when_attributes_missing(model, mocker):
    """PlateConnectionSolver.find_topology IS called when a plate joint is created without topology info."""
    plate1, plate2 = model.plates

    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")
    mock_find_topology.return_value = TopologyInfo(
        JointTopology.TOPO_EDGE_EDGE,
        distance=0.0,
        location=Point(5, 10, 0),
        element_topo_info={
            str(plate1.guid): PlateTopologyInfo(role="edge", edge_index=1),
            str(plate2.guid): PlateTopologyInfo(role="edge", edge_index=0),
        },
    )

    joint = PlateLButtJoint.create(model, plate1, plate2)

    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE
    assert joint.location == Point(5, 10, 0)
    assert joint.distance == 0.0
    mock_find_topology.assert_called_once_with(plate1, plate2)
