import pytest
from unittest import mock
from unittest.mock import Mock

from compas.geometry import Point
from compas.geometry import Line

from compas_timber.connections import NBeamKDTreeAnalyzer
from compas_timber.connections import CompositeAnalyzer
from compas_timber.connections import QuadAnalyzer
from compas_timber.connections import TripletAnalyzer
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections.analyzers import Cluster
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


def test_single_joint_cluster_topology():
    """Test that cluster with single joint returns the joint's topology."""
    # Create a mock joint with a specific topology
    mock_joint = Mock(spec=JointCandidate)
    mock_joint.topology = JointTopology.TOPO_L
    mock_joint.elements = [Mock(), Mock()]

    cluster = Cluster([mock_joint])

    assert cluster.topology == JointTopology.TOPO_L


def test_single_joint_cluster_different_topologies():
    """Test single joint clusters with different topology types."""
    test_cases = [JointTopology.TOPO_I, JointTopology.TOPO_L, JointTopology.TOPO_T, JointTopology.TOPO_X, JointTopology.TOPO_UNKNOWN]

    for topology in test_cases:
        mock_joint = Mock(spec=JointCandidate)
        mock_joint.topology = topology
        mock_joint.elements = [Mock(), Mock()]

        cluster = Cluster([mock_joint])
        assert cluster.topology == topology


def test_multiple_joints_with_valid_topologies_returns_valid_topo():
    """Test that cluster with multiple joints of valid topologies (L, I, T) returns TOPO_K."""
    # Create joints with valid topologies (all L, I, or T)
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_I
    joint2.elements = [Mock(), Mock()]

    joint3 = Mock(spec=JointCandidate)
    joint3.topology = JointTopology.TOPO_T
    joint3.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2, joint3])

    assert cluster.topology == JointTopology.TOPO_K


def test_multiple_joints_with_t_topology_returns_topo_k():
    """Test that cluster with at least one T joint returns TOPO_K."""
    # Create joints where at least one is T topology
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_T  # This should trigger TOPO_K
    joint2.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2])

    assert cluster.topology == JointTopology.TOPO_K


def test_multiple_joints_with_x_topology_returns_topo_k():
    """Test that cluster including TOPO_X returns TOPO_K."""
    # Create joints with one invalid topology
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_X
    joint2.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2])

    assert cluster.topology == JointTopology.TOPO_K


def test_multiple_joints_with_unknown_topology_returns_topo_unknown():
    """Test that cluster with TOPO_UNKNOWN joints returns TOPO_UNKNOWN."""
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_UNKNOWN
    joint2.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2])

    assert cluster.topology == JointTopology.TOPO_UNKNOWN


def test_multiple_joints_all_l_i_topologies_returns_topo_y():
    """Test that cluster with only L and I topologies returns TOPO_Y."""
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_I
    joint2.elements = [Mock(), Mock()]

    joint3 = Mock(spec=JointCandidate)
    joint3.topology = JointTopology.TOPO_L
    joint3.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2, joint3])

    assert cluster.topology == JointTopology.TOPO_Y


def test_t_topology_precedence_over_other_valid_topologies():
    """Test that T topology takes precedence and returns TOPO_K even with other valid topologies."""
    # Mix of L, I, and T - should return TOPO_K because of T
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_L
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_I
    joint2.elements = [Mock(), Mock()]

    joint3 = Mock(spec=JointCandidate)
    joint3.topology = JointTopology.TOPO_T
    joint3.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2, joint3])

    assert cluster.topology == JointTopology.TOPO_K


def test_multiple_t_joints_returns_topo_k():
    """Test that cluster with multiple T joints returns TOPO_K."""
    joint1 = Mock(spec=JointCandidate)
    joint1.topology = JointTopology.TOPO_T
    joint1.elements = [Mock(), Mock()]

    joint2 = Mock(spec=JointCandidate)
    joint2.topology = JointTopology.TOPO_T
    joint2.elements = [Mock(), Mock()]

    cluster = Cluster([joint1, joint2])

    assert cluster.topology == JointTopology.TOPO_K


def test_edge_cases_with_other_topology_values():
    """Test cluster topology with edge case topology values."""
    edge_case_topologies = [JointTopology.TOPO_Y, JointTopology.TOPO_K, JointTopology.TOPO_EDGE_EDGE, JointTopology.TOPO_EDGE_FACE]

    for topology in edge_case_topologies:
        joint1 = Mock(spec=JointCandidate)
        joint1.topology = JointTopology.TOPO_L
        joint1.elements = [Mock(), Mock()]

        joint2 = Mock(spec=JointCandidate)
        joint2.topology = topology  # Should make cluster return TOPO_UNKNOWN
        joint2.elements = [Mock(), Mock()]

        cluster = Cluster([joint1, joint2])

        assert cluster.topology == JointTopology.TOPO_UNKNOWN


def test_empty_cluster_topology():
    """Test topology behavior with empty cluster."""
    cluster = Cluster([])
    assert cluster.topology == JointTopology.TOPO_UNKNOWN


def test_kdtree_cache_reuses_same_instance(two_triplets_beams):
    """Two analyzers built from the same model must share the identical KDTree object."""
    model = TimberModel()
    model.add_elements(two_triplets_beams)
    model.connect_adjacent_beams()

    analyzer_a = NBeamKDTreeAnalyzer(model, n=2)
    analyzer_b = NBeamKDTreeAnalyzer(model, n=3)

    assert analyzer_a._kdtree is analyzer_b._kdtree


def test_kdtree_cache_rebuilds_after_model_change(two_triplets_beams):
    """After joints are added to the model, a new KDTree must be built."""
    model = TimberModel()
    model.add_elements(two_triplets_beams)
    model.connect_adjacent_beams()

    analyzer_before = NBeamKDTreeAnalyzer(model, n=2)
    tree_before = analyzer_before._kdtree

    # Add a new beam so that connect_adjacent_beams produces new joint candidates
    extra_beam = Beam.from_centerline(
        centerline=Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=50.0, y=-300.0, z=0.0)),
        height=12,
        width=6,
    )
    model.add_element(extra_beam)
    model.connect_adjacent_beams()

    analyzer_after = NBeamKDTreeAnalyzer(model, n=2)
    tree_after = analyzer_after._kdtree

    assert tree_after is not tree_before


def test_kdtree_ordering_consistency(two_triplets_beams):
    model = TimberModel()
    model.add_elements(two_triplets_beams)
    model.connect_adjacent_beams()

    analyzer_a = NBeamKDTreeAnalyzer(model, n=3)
    clusters_a = analyzer_a.find()
    expected = sorted([frozenset(id(e) for e in cluster.elements) for cluster in clusters_a])

    # Simulate a subsequent call to model.joint_candidates returning the same joints reversed.
    reversed_joints = list(reversed(analyzer_a._joints))
    with mock.patch.object(type(model), "joint_candidates", new_callable=mock.PropertyMock, return_value=reversed_joints):
        analyzer_b = NBeamKDTreeAnalyzer(model, n=3)
        assert analyzer_b._kdtree is analyzer_a._kdtree
        clusters_b = analyzer_b.find()

    actual = sorted([frozenset(id(e) for e in cluster.elements) for cluster in clusters_b])
    assert expected == actual
