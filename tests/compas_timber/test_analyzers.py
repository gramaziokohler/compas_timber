import pytest
from unittest.mock import Mock

from compas.geometry import Point
from compas.geometry import Line

from compas_timber.connections import NBeamKDTreeAnalyzer
from compas_timber.connections import CompositeAnalyzer
from compas_timber.connections import QuadAnalyzer
from compas_timber.connections import TripletAnalyzer
from compas_timber.connections import GenericJoint
from compas_timber.connections import JointTopology
from compas_timber.connections.analyzers import Cluster
from compas_timber.connections.analyzers import get_clusters_from_model
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def two_triplets_beams():
    height, width = (12, 6)

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
    ]

    return [Beam.from_centerline(centerline=line, height=height, width=width) for line in lines]


@pytest.fixture
def one_triplet_two_quads_beams():
    height, width = (12, 6)

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=90.0, y=-220.0, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=220.0, z=130.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=260.0, z=-120.0)),
    ]

    return [Beam.from_centerline(centerline=line, height=height, width=width) for line in lines]


def test_analyzer_empty_model():
    with pytest.raises(ValueError):
        _ = NBeamKDTreeAnalyzer(TimberModel())


def test_two_triplet_analyzer(two_triplets_beams):
    model = TimberModel()
    model.add_elements(two_triplets_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=3)

    clusters = analyzer.find()
    assert len(clusters) == 2
    assert all(len(cluster) == 3 for cluster in clusters)


def test_one_triplet_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=3)

    clusters = analyzer.find()
    assert len(clusters) == 1  # We expect two triplets from the provided beams
    assert len(clusters[0]) == 3


def test_two_quads_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=4)

    clusters = analyzer.find()
    assert len(clusters) == 2
    assert all(len(cluster) == 4 for cluster in clusters)


def test_composite_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = CompositeAnalyzer.from_model(model=model, analyzers_cls=[QuadAnalyzer, TripletAnalyzer])

    clusters = analyzer.find()

    triplets = [cluster for cluster in clusters if len(cluster) == 3]
    quads = [cluster for cluster in clusters if len(cluster) == 4]
    assert len(triplets) == 1
    assert len(quads) == 2


@pytest.fixture
def beams():

    w = 0.2
    h = 0.2
    lines = [
        Line(Point(1, 0, 0), Point(-1, 0, 0)),
        Line(Point(1, 0, 0), Point(1, 2, 0)),
        Line(Point(1, 0, 0), Point(1, -1, 0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def beams_one_separated():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(1, 0, 0), Point(-1, 0, 0)),
        Line(Point(1, 0, 0), Point(1, 2, 0)),
        Line(Point(1, 0, 0), Point(1, -1, 0.05)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]



@pytest.fixture
def beams_all_separated():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(1, 0, 0), Point(-1, 0, -0.05)),
        Line(Point(1, 0, 0), Point(1, 2, 0)),
        Line(Point(1, 0, 0), Point(1, -1, 0.05)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]

def test_get_clusters_from_model_connected(beams):
    model = TimberModel()
    model.add_elements(beams)
    clusters = get_clusters_from_model(model)

    assert len(clusters) ==1
    assert isinstance(clusters[0], Cluster)
    assert len(list(clusters[0].elements)) == 3

def test_get_clusters_from_model_one_separate(beams_one_separated):
    model = TimberModel()
    model.add_elements(beams_one_separated)
    clusters = get_clusters_from_model(model)

    assert len(clusters) == 1
    assert isinstance(clusters[0], Cluster)
    assert len(list(clusters[0].elements)) == 2

def test_get_clusters_from_model_all_separate(beams_all_separated):
    model = TimberModel()
    model.add_elements(beams_all_separated)
    clusters = get_clusters_from_model(model)

    assert len(clusters) == 0

def test_get_clusters_from_model_one_separate_with_distance(beams_one_separated):
    model = TimberModel()
    model.add_elements(beams_one_separated)
    clusters = get_clusters_from_model(model, max_distance=0.1)

    assert len(clusters) ==1
    assert isinstance(clusters[0], Cluster)
    assert len(list(clusters[0].elements)) == 3

def test_get_clusters_from_model_all_separate_with_distance(beams_all_separated):
    model = TimberModel()
    model.add_elements(beams_all_separated)
    clusters = get_clusters_from_model(model)

    assert len(clusters) == 0
    assert isinstance(clusters[0], Cluster)
    assert len(list(clusters[0].elements)) == 3

class TestClusterTopology:
    """Test cases for the topology property of the Cluster class."""

    def test_single_joint_cluster_topology(self):
        """Test that cluster with single joint returns the joint's topology."""
        # Create a mock joint with a specific topology
        mock_joint = Mock(spec=GenericJoint)
        mock_joint.topology = JointTopology.TOPO_L
        mock_joint.elements = [Mock(), Mock()]

        cluster = Cluster([mock_joint])

        assert cluster.topology == JointTopology.TOPO_L

    def test_single_joint_cluster_different_topologies(self):
        """Test single joint clusters with different topology types."""
        test_cases = [JointTopology.TOPO_I, JointTopology.TOPO_L, JointTopology.TOPO_T, JointTopology.TOPO_X, JointTopology.TOPO_UNKNOWN]

        for topology in test_cases:
            mock_joint = Mock(spec=GenericJoint)
            mock_joint.topology = topology
            mock_joint.elements = [Mock(), Mock()]

            cluster = Cluster([mock_joint])
            assert cluster.topology == topology

    def test_multiple_joints_with_valid_topologies_returns_topo_y(self):
        """Test that cluster with multiple joints of valid topologies (L, I, T) returns TOPO_Y."""
        # Create joints with valid topologies (all L, I, or T)
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_I
        joint2.elements = [Mock(), Mock()]

        joint3 = Mock(spec=GenericJoint)
        joint3.topology = JointTopology.TOPO_L
        joint3.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2, joint3])

        assert cluster.topology == JointTopology.TOPO_Y

    def test_multiple_joints_with_t_topology_returns_topo_k(self):
        """Test that cluster with at least one T joint returns TOPO_K."""
        # Create joints where at least one is T topology
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_T  # This should trigger TOPO_K
        joint2.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2])

        assert cluster.topology == JointTopology.TOPO_K

    def test_multiple_joints_with_invalid_topology_returns_topo_unknown(self):
        """Test that cluster with any invalid topology returns TOPO_UNKNOWN."""
        # Create joints with one invalid topology
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_X
        joint2.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2])

        assert cluster.topology == JointTopology.TOPO_K

    def test_multiple_joints_with_unknown_topology_returns_topo_unknown(self):
        """Test that cluster with TOPO_UNKNOWN joints returns TOPO_UNKNOWN."""
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_UNKNOWN
        joint2.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2])

        assert cluster.topology == JointTopology.TOPO_UNKNOWN

    def test_multiple_joints_all_l_i_topologies_returns_topo_y(self):
        """Test that cluster with only L and I topologies returns TOPO_Y."""
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_I
        joint2.elements = [Mock(), Mock()]

        joint3 = Mock(spec=GenericJoint)
        joint3.topology = JointTopology.TOPO_L
        joint3.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2, joint3])

        assert cluster.topology == JointTopology.TOPO_Y

    def test_t_topology_precedence_over_other_valid_topologies(self):
        """Test that T topology takes precedence and returns TOPO_K even with other valid topologies."""
        # Mix of L, I, and T - should return TOPO_K because of T
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_I
        joint2.elements = [Mock(), Mock()]

        joint3 = Mock(spec=GenericJoint)
        joint3.topology = JointTopology.TOPO_T
        joint3.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2, joint3])

        assert cluster.topology == JointTopology.TOPO_K

    def test_multiple_t_joints_returns_topo_k(self):
        """Test that cluster with multiple T joints returns TOPO_K."""
        joint1 = Mock(spec=GenericJoint)
        joint1.topology = JointTopology.TOPO_T
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=GenericJoint)
        joint2.topology = JointTopology.TOPO_T
        joint2.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2])

        assert cluster.topology == JointTopology.TOPO_K

    def test_edge_cases_with_other_topology_values(self):
        """Test cluster topology with edge case topology values."""
        edge_case_topologies = [JointTopology.TOPO_Y, JointTopology.TOPO_K, JointTopology.TOPO_EDGE_EDGE, JointTopology.TOPO_EDGE_FACE]

        for topology in edge_case_topologies:
            joint1 = Mock(spec=GenericJoint)
            joint1.topology = JointTopology.TOPO_L
            joint1.elements = [Mock(), Mock()]

            joint2 = Mock(spec=GenericJoint)
            joint2.topology = topology  # Should make cluster return TOPO_UNKNOWN
            joint2.elements = [Mock(), Mock()]

            cluster = Cluster([joint1, joint2])

            assert cluster.topology == JointTopology.TOPO_UNKNOWN

    def test_empty_cluster_topology(self):
        """Test topology behavior with empty cluster."""
        cluster = Cluster([])
        assert cluster.topology == JointTopology.TOPO_UNKNOWN

