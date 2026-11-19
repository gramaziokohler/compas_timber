import pytest
from unittest.mock import Mock

from compas.geometry import Point
from compas_timber.connections.utilities import (
    parse_cross_beams_and_main_beams_from_cluster,
)
from compas_timber.connections.solver import JointTopology
from compas_timber.elements import Beam
from compas_timber.connections import Cluster


@pytest.fixture
def sample_beams():
    """Create sample beams for testing."""
    beam_a = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    beam_b = Beam.from_endpoints(Point(0, 0, 0), Point(0, 10, 0), 1, 1)
    beam_c = Beam.from_endpoints(Point(0, 10, 0), Point(10, 10, 0), 1, 1)
    beam_d = Beam.from_endpoints(Point(10, 0, 0), Point(10, 10, 0), 1, 1)
    return beam_a, beam_b, beam_c, beam_d


def create_mock_joint(topology, elements):
    """Helper to create a mock joint with given topology and elements."""
    joint = Mock()
    joint.topology = topology
    joint.elements = elements
    return joint


def test_parse_l_topology_single_joint(sample_beams):
    """Test parsing L-topology joint (end-to-end between two non-parallel beams)."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # L-topology: both elements are considered main beams
    joint = create_mock_joint(JointTopology.TOPO_L, [beam_a, beam_b])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert len(cross_beams) == 0
    assert len(main_beams) == 2
    assert set(main_beams) == {beam_a, beam_b}


def test_parse_t_topology_single_joint(sample_beams):
    """Test parsing T-topology joint (end-to-middle connection)."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # T-topology: first element is main beam, second is cross beam
    joint = create_mock_joint(JointTopology.TOPO_T, [beam_a, beam_b])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert len(cross_beams) == 1
    assert len(main_beams) == 1
    assert beam_b in cross_beams
    assert beam_a in main_beams


def test_parse_x_topology_single_joint(sample_beams):
    """Test parsing X-topology joint (middle-to-middle connection)."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # X-topology: both elements are cross beams
    joint = create_mock_joint(JointTopology.TOPO_X, [beam_a, beam_b])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert len(cross_beams) == 2
    assert len(main_beams) == 0
    assert set(cross_beams) == {beam_a, beam_b}


def test_parse_mixed_topologies(sample_beams):
    """Test parsing cluster with multiple joints of different topologies."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # Create joints with different topologies
    l_joint = create_mock_joint(JointTopology.TOPO_L, [beam_a, beam_b])
    t_joint = create_mock_joint(JointTopology.TOPO_T, [beam_c, beam_d])

    cluster = Cluster([l_joint, t_joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    # From L-joint: both beam_a and beam_b are main beams
    # From T-joint: beam_c is main beam, beam_d is cross beam
    assert beam_d in cross_beams
    assert set(main_beams) == {beam_a, beam_b, beam_c}


def test_parse_duplicates_removed(sample_beams):
    """Test that duplicate beams are removed from the result lists."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # Create two joints that share a beam
    l_joint = create_mock_joint(JointTopology.TOPO_L, [beam_a, beam_b])
    t_joint = create_mock_joint(JointTopology.TOPO_T, [beam_a, beam_c])  # beam_a appears twice

    cluster = Cluster([l_joint, t_joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    # beam_a should appear only once in main_beams
    assert main_beams.count(beam_a) <= 1
    assert len(set(main_beams)) == len(main_beams), "Duplicates not removed from main_beams"
    assert len(set(cross_beams)) == len(cross_beams), "Duplicates not removed from cross_beams"


def test_parse_complex_cluster(sample_beams):
    """Test parsing a complex cluster with multiple joint types."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # Create a more complex scenario
    l_joint = create_mock_joint(JointTopology.TOPO_L, [beam_a, beam_b])
    t_joint = create_mock_joint(JointTopology.TOPO_T, [beam_a, beam_c])
    x_joint = create_mock_joint(JointTopology.TOPO_X, [beam_c, beam_d])

    cluster = Cluster([l_joint, t_joint, x_joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    # beam_a, beam_b: from L-joint (both main)
    # beam_a, beam_c: from T-joint (beam_a main, beam_c cross)
    # beam_c, beam_d: from X-joint (both cross)

    # After deduplication:
    # main_beams should contain: beam_a, beam_b
    # cross_beams should contain: beam_c, beam_d

    assert set(main_beams) == {beam_a, beam_b}
    assert set(cross_beams) == {beam_c, beam_d}


def test_parse_empty_cluster():
    """Test parsing an empty cluster."""
    cluster = Cluster([])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert len(cross_beams) == 0
    assert len(main_beams) == 0


def test_parse_single_beam_l_joint(sample_beams):
    """Test L-topology with single element (edge case)."""
    beam_a, beam_b, _, _ = sample_beams

    # L-topology technically expects 2 beams, but test with 1
    joint = create_mock_joint(JointTopology.TOPO_L, [beam_a])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert len(cross_beams) == 0
    assert len(main_beams) == 1
    assert beam_a in main_beams


def test_parse_unknown_topology(sample_beams):
    """Test that TOPO_UNKNOWN is ignored."""
    beam_a, beam_b, _, _ = sample_beams

    # TOPO_UNKNOWN should not match any condition
    joint = create_mock_joint(JointTopology.TOPO_UNKNOWN, [beam_a, beam_b])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    # Beams should not be added since topology doesn't match any case
    assert len(cross_beams) == 0
    assert len(main_beams) == 0


def test_parse_multiple_beams_x_topology(sample_beams):
    """Test X-topology with more than 2 elements."""
    beam_a, beam_b, beam_c, beam_d = sample_beams

    # X-topology with 4 beams (unusual but test robustness)
    joint = create_mock_joint(JointTopology.TOPO_X, [beam_a, beam_b, beam_c, beam_d])
    cluster = Cluster([joint])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert set(cross_beams) == {beam_a, beam_b, beam_c, beam_d}
    assert len(main_beams) == 0


def test_parse_return_types():
    """Test that return values are lists."""
    cluster = Cluster([])

    cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)

    assert isinstance(cross_beams, list)
    assert isinstance(main_beams, list)
