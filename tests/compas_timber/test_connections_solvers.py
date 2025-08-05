import pytest
from compas_timber.elements import Beam
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas.geometry import Point
from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas.geometry import Polyline
from compas_timber.utils import distance_segment_segment
from compas.tolerance import TOL


def flip_beam(beam):
    return Beam.from_endpoints(beam.centerline.end, beam.centerline.start, beam.width, beam.height)


@pytest.fixture
def i_beams():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(-10, 0, 0), Point(0, 0, 0), 1, 1),
        Beam.from_endpoints(Point(10, 0, 0), Point(20, 0, 0), 1, 1),
    ]
    return first_beam, connecting_beams


@pytest.fixture
def overlap_i_beams():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(0.01, 0, 0), Point(10, 0, 0), 1, 1),
        Beam.from_endpoints(Point(0, 0, 0), Point(9.99, 0, 0), 1, 1),
        Beam.from_endpoints(Point(0, 0, 0), Point(10.01, 0, 0), 1, 1),
        Beam.from_endpoints(Point(-0.01, 0, 0), Point(10, 0, 0), 1, 1),
    ]
    return first_beam, connecting_beams


@pytest.fixture
def i_beams_with_tolerance():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(-10, 0, 0), Point(-0.01, 0, 0), 1, 1),
        Beam.from_endpoints(Point(10.01, 0, 0), Point(20, 0, 0), 1, 1),
        Beam.from_endpoints(Point(-10, 0, 0), Point(0.01, 0, 0), 1, 1),
        Beam.from_endpoints(Point(9.99, 0, 0), Point(20, 0, 0), 1, 1),
    ]
    return first_beam, connecting_beams


def test_find_topology_i_beams(i_beams):
    for beam_a in [i_beams[0], flip_beam(i_beams[0])]:
        for bb in i_beams[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology == JointTopology.TOPO_I, "Expected I-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, 0.0), "Expected distance == 0"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


def test_find_topology_tolerance_no_max_dist(i_beams_with_tolerance):
    for beam_a in [i_beams_with_tolerance[0], flip_beam(i_beams_with_tolerance[0])]:
        for bb in i_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
                assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results for I_Topo beams with tolerance"


def test_find_topology_i_beams_with_max_dist(i_beams_with_tolerance):
    for beam_a in [i_beams_with_tolerance[0], flip_beam(i_beams_with_tolerance[0])]:
        for bb in i_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
                assert topo_results.topology == JointTopology.TOPO_I, "Expected I-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, 0.01), "Expected distance == 0.001"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


def test_find_topology_i_beams_overlap(overlap_i_beams):
    for beam_a in [overlap_i_beams[0], flip_beam(overlap_i_beams[0])]:
        for bb in overlap_i_beams[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
                assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results for I_Topo beams with tolerance"


def test_find_topology_i_beams_overlap_max_dist(overlap_i_beams):
    for beam_a in [overlap_i_beams[0], flip_beam(overlap_i_beams[0])]:
        for bb in overlap_i_beams[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
                assert topo_results.topology == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
                assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results for I_Topo beams with tolerance"


@pytest.fixture
def l_beams():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(0, 0, 0), Point(0, 10, 0), 1, 1),
    ]
    return first_beam, connecting_beams


@pytest.fixture
def l_beams_with_tolerance():
    first_beam = Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(-0.01, 0, 0), Point(-0.01, 10, 0), 1, 1),  # gap
        Beam.from_endpoints(Point(0, -0.01, 0), Point(0, 10.01, 0), 1, 1),  # beam_b cross
        Beam.from_endpoints(Point(0.01, 0, 0), Point(0.01, 10, 0), 1, 1),  # beam_a cross
        Beam.from_endpoints(Point(0.01, -0.01, 0), Point(0.01, 10, 0), 1, 1),  # topo_x
        Beam.from_endpoints(Point(0.01, -0.01, 0.01), Point(0.01, 10, 0.01), 1, 1),  # topo_x with z-gap
    ]
    return first_beam, connecting_beams


def test_find_topology_l_beams(l_beams):
    for beam_a in [l_beams[0], flip_beam(l_beams[0])]:
        for bb in l_beams[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology == JointTopology.TOPO_L, "Expected I-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, 0.0), "Expected distance == 0"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


def test_find_l_topology_tolerance_no_max_dist(l_beams_with_tolerance):
    for beam_a in [l_beams_with_tolerance[0], flip_beam(l_beams_with_tolerance[0])]:
        for bb in l_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology != JointTopology.TOPO_L, "Expected joint topology {}".format(JointTopology.get_name(topo_results.topology))


def test_find_topology_l_beams_with_max_dist(l_beams_with_tolerance):
    for beam_a in [l_beams_with_tolerance[0], flip_beam(l_beams_with_tolerance[0])]:
        for bb in l_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                dist = distance_segment_segment(beam_a.centerline, beam_b.centerline)
                topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
                assert topo_results.topology == JointTopology.TOPO_L, "Expected I-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, dist), "Expected distance == 0.01"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


@pytest.fixture
def t_beams():
    first_beam = Beam.from_endpoints(Point(-5, 0, 0), Point(5, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(-5, -5, 0), Point(-5, 5, 0), 1, 1),
        Beam.from_endpoints(Point(5, -5, 0), Point(5, 5, 0), 1, 1),
    ]
    return first_beam, connecting_beams


@pytest.fixture
def t_beams_with_tolerance():
    first_beam = Beam.from_endpoints(Point(-5, 0, 0), Point(5, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(-5.01, -5, 0), Point(-5.01, 5, 0), 1, 1),  # gap
        Beam.from_endpoints(Point(5.01, -5, 0), Point(5.01, 5, 0), 1, 1),  # gap
        Beam.from_endpoints(Point(-4.99, -5, 0), Point(-4.99, 5, 0), 1, 1),  # x_topo
        Beam.from_endpoints(Point(-5, -5, 0.01), Point(-5, 5, 0.01), 1, 1),  # vertical gap
    ]
    return first_beam, connecting_beams


def test_find_topology_t_beams(t_beams):
    for beam_a in [t_beams[0], flip_beam(t_beams[0])]:
        for bb in t_beams[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology == JointTopology.TOPO_T, "Expected I-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, 0.0), "Expected distance == 0"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


def test_find_t_topology_tolerance_no_max_dist(t_beams_with_tolerance):
    for beam_a in [t_beams_with_tolerance[0], flip_beam(t_beams_with_tolerance[0])]:
        for bb in t_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                topo_results = cs.find_topology(beam_a, beam_b)
                assert topo_results.topology != JointTopology.TOPO_T, "Expected joint topology {}".format(JointTopology.get_name(topo_results.topology))


def test_find_topology_t_beams_with_max_dist(t_beams_with_tolerance):
    for beam_a in [t_beams_with_tolerance[0], flip_beam(t_beams_with_tolerance[0])]:
        for bb in t_beams_with_tolerance[1]:
            for beam_b in [bb, flip_beam(bb)]:
                cs = ConnectionSolver()
                dist = distance_segment_segment(beam_a.centerline, beam_b.centerline)
                topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
                assert topo_results.topology == JointTopology.TOPO_T, "Expected T-beam joint topology"
                assert topo_results.beam_a == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_b == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, dist), "Expected distance == 0.01"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


def test_find_topology_t_beams_with_max_dist_flip_role(t_beams_with_tolerance):
    for bb in t_beams_with_tolerance[1]:
        for beam_a in [bb, flip_beam(bb)]:
            for beam_b in [t_beams_with_tolerance[0], flip_beam(t_beams_with_tolerance[0])]:
                cs = ConnectionSolver()
                dist = distance_segment_segment(beam_a.centerline, beam_b.centerline)
                topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
                assert topo_results.topology == JointTopology.TOPO_T, "Expected T-beam joint topology"
                assert topo_results.beam_b == beam_a, "Expected first beam as first plate in topology result"
                assert topo_results.beam_a == beam_b, "Expected second beam as second plate in topology result"
                assert TOL.is_close(topo_results.distance, dist), "Expected distance == 0.01"
                assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


@pytest.fixture
def x_beams():
    first_beam = Beam.from_endpoints(Point(-5, 0, 0), Point(5, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(0, -5, 0), Point(0, 5, 0), 1, 1),
    ]
    return first_beam, connecting_beams


@pytest.fixture
def x_beams_with_tolerance():
    first_beam = Beam.from_endpoints(Point(-5, 0, 0), Point(5, 0, 0), 1, 1)
    connecting_beams = [
        Beam.from_endpoints(Point(0, -5, 0.01), Point(0, 5, 0.01), 1, 1),
    ]
    return first_beam, connecting_beams


def test_plate_L_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_a, plate_b)
    assert topo_results.topology == JointTopology.TOPO_EDGE_EDGE, "Expected L-joint topology"
    assert topo_results.plate_a == plate_a, "Expected plate_a as first plate in topology result"
    assert topo_results.plate_b == plate_b, "Expected plate_b as second plate in topology result"
    assert topo_results.segment_a_index == 1, "Expected connection segment at index = 1"
    assert topo_results.segment_b_index == 0, "Expected connection segment at index = 0"


def test_plate_T_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_a, plate_b)
    assert topo_results.topology == JointTopology.TOPO_EDGE_FACE, "Expected T-joint topology"
    assert topo_results.plate_a == plate_b, "Expected plate_a as first plate in topology result"
    assert topo_results.plate_b == plate_a, "Expected plate_b as second plate in topology result"
    assert topo_results.segment_a_index == 0, "Expected connection segment at index = 1"
    assert topo_results.segment_b_index is None, "Expected connection segment at index = 0"


def test_reversed_plate_T_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_b, plate_a)
    assert topo_results.topology == JointTopology.TOPO_EDGE_FACE, "Expected T-joint topology"
    assert topo_results.plate_a == plate_b, "Expected plate_a as first plate in topology result"
    assert topo_results.plate_b == plate_a, "Expected plate_b as second plate in topology result"
    assert topo_results.segment_a_index == 0, "Expected connection segment at index = 1"
    assert topo_results.segment_b_index is None, "Expected connection segment at index = 0"


def test_three_plate_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    topo_results = []

    cs = PlateConnectionSolver()

    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    assert len(topo_results) == 3, "Expected three topology results"
    assert all(tr.topology == JointTopology.TOPO_EDGE_EDGE for tr in topo_results), "Expected all topology results to be L-joints"


def test_three_plate_mix_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    topo_results = []

    cs = PlateConnectionSolver()

    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    assert len(topo_results) == 3, "Expected three topology results"
    assert topo_results[0].topology == JointTopology.TOPO_EDGE_FACE, "Expected first topology result to be T-joint"
    assert topo_results[1].topology == JointTopology.TOPO_EDGE_EDGE, "Expected second topology result to be L-joint"
    assert topo_results[2].topology == JointTopology.TOPO_EDGE_EDGE, "Expected third topology result to be L-joint"
