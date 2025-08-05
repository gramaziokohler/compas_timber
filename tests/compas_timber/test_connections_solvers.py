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


@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
@pytest.mark.parametrize(
    "beam_fixture,expected_topology", [("i_beams", JointTopology.TOPO_I), ("l_beams", JointTopology.TOPO_L), ("t_beams", JointTopology.TOPO_T), ("x_beams", JointTopology.TOPO_X)]
)
def test_find_topology_basic(beam_fixture, expected_topology, flip_a, flip_b, request):
    """Test basic topology finding for different beam configurations."""
    beam_config = request.getfixturevalue(beam_fixture)
    beam_a = flip_beam(beam_config[0]) if flip_a else beam_config[0]

    for connecting_beam in beam_config[1]:
        beam_b = flip_beam(connecting_beam) if flip_b else connecting_beam

        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)
        assert topo_results.topology == expected_topology, f"Expected {expected_topology} joint topology"
        assert topo_results.beam_a == beam_a, "Expected first beam as beam_a in topology result"
        assert topo_results.beam_b == beam_b, "Expected second beam as beam_b in topology result"
        assert TOL.is_close(topo_results.distance, 0.0), "Expected distance == 0"
        assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
@pytest.mark.parametrize("beam_fixture", ["i_beams_with_tolerance", "l_beams_with_tolerance", "t_beams_with_tolerance", "x_beams_with_tolerance"])
def test_find_topology_tolerance_no_max_dist(beam_fixture, flip_a, flip_b, request):
    """Test topology finding with tolerance but no max_distance - should return UNKNOWN or non-matching topology."""
    beam_config = request.getfixturevalue(beam_fixture)
    beam_a = flip_beam(beam_config[0]) if flip_a else beam_config[0]

    for connecting_beam in beam_config[1]:
        beam_b = flip_beam(connecting_beam) if flip_b else connecting_beam

        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)

        # For i_beams_with_tolerance, expect UNKNOWN; for others, expect topology != original type
        if beam_fixture == "i_beams_with_tolerance":
            assert topo_results.topology == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
            assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results"
        else:
            # For L, T, X beams with tolerance, they should not match their expected topology without max_distance
            expected_topo_map = {"l_beams_with_tolerance": JointTopology.TOPO_L, "t_beams_with_tolerance": JointTopology.TOPO_T, "x_beams_with_tolerance": JointTopology.TOPO_X}
            expected_topology = expected_topo_map[beam_fixture]
            assert topo_results.topology != expected_topology, f"Expected joint topology != {expected_topology}"


@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
@pytest.mark.parametrize(
    "beam_fixture,expected_topology",
    [
        ("i_beams_with_tolerance", JointTopology.TOPO_I),
        ("l_beams_with_tolerance", JointTopology.TOPO_L),
        ("t_beams_with_tolerance", JointTopology.TOPO_T),
        ("x_beams_with_tolerance", JointTopology.TOPO_X),
    ],
)
def test_find_topology_with_max_distance(beam_fixture, expected_topology, flip_a, flip_b, request):
    """Test topology finding with max_distance tolerance for all beam types."""
    beam_config = request.getfixturevalue(beam_fixture)
    beam_a = flip_beam(beam_config[0]) if flip_a else beam_config[0]

    for connecting_beam in beam_config[1]:
        beam_b = flip_beam(connecting_beam) if flip_b else connecting_beam

        cs = ConnectionSolver()
        dist = distance_segment_segment(beam_a.centerline, beam_b.centerline)
        topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)

        assert topo_results.topology == expected_topology, f"Expected {expected_topology} joint topology"
        assert topo_results.beam_a == beam_a, "Expected first beam as beam_a in topology result"
        assert topo_results.beam_b == beam_b, "Expected second beam as beam_b in topology result"

        # For i_beams_with_tolerance, distance is consistently 0.01; for others it varies
        expected_distance = 0.01 if beam_fixture == "i_beams_with_tolerance" else dist
        assert TOL.is_close(topo_results.distance, expected_distance), f"Expected distance == {expected_distance}"
        assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
@pytest.mark.parametrize(
    "fixture_name,expected_topology",
    [
        ("overlap_i_beams", JointTopology.TOPO_UNKNOWN),
    ],
)
def test_find_topology_overlap_beams(fixture_name, expected_topology, flip_a, flip_b, request):
    """Test topology finding for overlapping beam configurations."""
    beam_config = request.getfixturevalue(fixture_name)
    beam_a = flip_beam(beam_config[0]) if flip_a else beam_config[0]

    for connecting_beam in beam_config[1]:
        beam_b = flip_beam(connecting_beam) if flip_b else connecting_beam

        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b)
        assert topo_results.topology == expected_topology, f"Expected {expected_topology} joint topology"
        assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results for overlapping beams"


@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
def test_find_topology_overlap_beams_with_max_dist(overlap_i_beams, flip_a, flip_b):
    """Test overlapping I-beam topology with max_distance - should still return UNKNOWN."""
    beam_a = flip_beam(overlap_i_beams[0]) if flip_a else overlap_i_beams[0]

    for connecting_beam in overlap_i_beams[1]:
        beam_b = flip_beam(connecting_beam) if flip_b else connecting_beam

        cs = ConnectionSolver()
        topo_results = cs.find_topology(beam_a, beam_b, max_distance=0.02)
        assert topo_results.topology == JointTopology.TOPO_UNKNOWN, "Expected unknown joint topology"
        assert all([v is None for v in [topo_results.distance, topo_results.location]]), "Expected no valid topology results for overlapping beams with tolerance"


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


@pytest.mark.parametrize(
    "plate_config,expected_topology,expected_segments",
    [
        ("plate_l_config", JointTopology.TOPO_EDGE_EDGE, (1, 0)),
        ("plate_t_config", JointTopology.TOPO_EDGE_FACE, (0, None)),
        ("plate_t_reversed_config", JointTopology.TOPO_EDGE_FACE, (0, None)),
    ],
)
def test_plate_topology(plate_config, expected_topology, expected_segments, request):
    """Test plate topology finding for different configurations."""
    plate_a, plate_b = request.getfixturevalue(plate_config)

    cs = PlateConnectionSolver()
    topo_results = cs.find_topology(plate_a, plate_b)

    assert topo_results.topology == expected_topology, f"Expected {expected_topology} topology"

    if expected_topology == JointTopology.TOPO_EDGE_EDGE:
        assert topo_results.plate_a == plate_a, "Expected plate_a as first plate"
        assert topo_results.plate_b == plate_b, "Expected plate_b as second plate"
        assert topo_results.segment_a_index == expected_segments[0], f"Expected segment_a_index = {expected_segments[0]}"
        assert topo_results.segment_b_index == expected_segments[1], f"Expected segment_b_index = {expected_segments[1]}"
    elif expected_topology == JointTopology.TOPO_EDGE_FACE:
        # For T-joints, the roles may be swapped
        assert topo_results.segment_a_index == expected_segments[0], f"Expected segment_a_index = {expected_segments[0]}"
        assert topo_results.segment_b_index == expected_segments[1], f"Expected segment_b_index = {expected_segments[1]}"


@pytest.fixture
def plate_l_config():
    """L-joint plate configuration."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    return plate_a, plate_b


@pytest.fixture
def plate_t_config():
    """T-joint plate configuration."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    return plate_a, plate_b


@pytest.fixture
def plate_t_reversed_config():
    """T-joint plate configuration with reversed input order."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    return plate_b, plate_a  # Reversed order


def test_three_plate_topology_combinations():
    """Test topology finding for three plates with different joint types."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()

    topo_ab = cs.find_topology(plate_a, plate_b)
    topo_cb = cs.find_topology(plate_c, plate_b)
    topo_ac = cs.find_topology(plate_a, plate_c)

    topo_results = [topo_ab, topo_cb, topo_ac]

    assert len(topo_results) == 3, "Expected three topology results"
    assert all(tr.topology == JointTopology.TOPO_EDGE_EDGE for tr in topo_results), "Expected all topology results to be L-joints"


def test_three_plate_mixed_topology():
    """Test topology finding for three plates with mixed joint types."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()

    topo_ab = cs.find_topology(plate_a, plate_b)
    topo_cb = cs.find_topology(plate_c, plate_b)
    topo_ac = cs.find_topology(plate_a, plate_c)

    expected_topologies = [JointTopology.TOPO_EDGE_FACE, JointTopology.TOPO_EDGE_EDGE, JointTopology.TOPO_EDGE_EDGE]
    actual_topologies = [topo_ab.topology, topo_cb.topology, topo_ac.topology]

    assert len(actual_topologies) == 3, "Expected three topology results"
    assert actual_topologies == expected_topologies, f"Expected {expected_topologies}, got {actual_topologies}"
