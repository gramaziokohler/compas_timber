import pytest
from compas_timber.elements import Beam
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas.geometry import Line, Point
from compas.tolerance import TOL

@pytest.fixture
def i_beams():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1,1)
    connecting_beams = [
        Beam.from_endpoints(Point(-10, 0, 0), Point(0, 0, 0), 1,1),
        Beam.from_endpoints(Point(10, 0, 0), Point(20, 0, 0), 1,1),
    ]
    return first_beam, connecting_beams

@pytest.fixture
def overlap_i_beams():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1,1)
    connecting_beams = [
        Beam.from_endpoints(Point(0.01, 0, 0), Point(10, 0, 0), 1,1),
        Beam.from_endpoints(Point(0, 0, 0), Point(9.99, 0, 0), 1,1),
        Beam.from_endpoints(Point(0, 0, 0), Point(10.01, 0, 0), 1,1),
        Beam.from_endpoints(Point(-0.01, 0, 0), Point(10, 0, 0), 1,1),
    ]
    return first_beam, connecting_beams



@pytest.fixture
def i_beams_with_tolerance():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1,1)
    connecting_beams = [
        Beam.from_endpoints(Point(-10, 0, 0), Point(-0.01, 0, 0), 1,1),
        Beam.from_endpoints(Point(10.01, 0, 0), Point(20, 0, 0), 1,1),
        Beam.from_endpoints(Point(-10, 0, 0), Point(0.01, 0, 0), 1,1),
        Beam.from_endpoints(Point(9.99, 0, 0), Point(20, 0, 0), 1,1),
    ]
    return first_beam, connecting_beams

def test_find_topology_i_beams(i_beams):
    beam_a = i_beams[0]
    for beam_b in i_beams[1]:
        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)
        assert topo_results[0] == JointTopology.TOPO_I, "Expected I-beam joint topology"
        assert topo_results[1] == beam_a, "Expected first beam as first plate in topology result"
        assert topo_results[2] == beam_b, "Expected second beam as second plate in topology result"
        assert TOL.is_close(topo_results[3], 0.0), "Expected distance == 0"
        assert isinstance(topo_results[4], Point), "Expected location to be a Point instance"

def test_find_topology_i_beams_no_max_dist(i_beams_with_tolerance):
    beam_a = i_beams_with_tolerance[0]
    for beam_b in i_beams_with_tolerance[1]:
        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)
        assert topo_results[0] == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
        assert all([v == None for v in topo_results[1:]]), "Expected no valid topology results for I_Topo beams with tolerance"

def test_find_topology_i_beams_overlap(overlap_i_beams):
    beam_a = overlap_i_beams[0]
    for beam_b in overlap_i_beams[1]:
        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)
        assert topo_results[0] == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
        assert all([v == None for v in topo_results[1:]]), "Expected no valid topology results for I_Topo beams with tolerance"

def test_find_topology_i_beams_overlap_max_dist(overlap_i_beams):
    beam_a = overlap_i_beams[0]
    for beam_b in overlap_i_beams[1]:
        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
        assert topo_results[0] == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
        assert all([v == None for v in topo_results[1:]]), "Expected no valid topology results for I_Topo beams with tolerance"

def test_find_topology_i_beams_with_max_dist(i_beams_with_tolerance):
    beam_a = i_beams_with_tolerance[0]
    for beam_b in i_beams_with_tolerance[1]:
        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
        assert topo_results[0] == JointTopology.TOPO_I, "Expected I-beam joint topology"
        assert topo_results[1] == beam_a, "Expected first beam as first plate in topology result"
        assert topo_results[2] == beam_b, "Expected second beam as second plate in topology result"
        assert TOL.is_close(topo_results[3], 0.01), "Expected distance == 0.001"
        assert isinstance(topo_results[4], Point), "Expected location to be a Point instance"