import pytest
from compas_timber.elements import Beam
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas.geometry import Point
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import distance_point_point
from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import PlateTopologyInfo
from compas_timber.connections import TopologyInfo
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
        main, other = topo_results.get_element_by_role(beam_a, beam_b)
        assert main is beam_a and other is beam_b, "Expected first beam ordered first in topology result"
        assert TOL.is_close(topo_results.distance, 0.0), "Expected distance == 0"
        assert isinstance(topo_results.location, Point), "Expected location to be a Point instance"


# Per-beam metadata cases. For I, the beams are parallel, so neither has a ref side facing the other. The T and X joints are deliberately off-centre on the beams that pass
# through: at an exact midpoint "the end closest to the joint" is a tie, and the ref side picked by
# `beam_ref_side_incidence` would depend on tie-breaking rather than on the geometry.
# Each beam entry is (start, end, role, expected ref side normal); the ref side faces the way the
# other beam runs from the joint, away from its own end nearest the joint.
BEAM_METADATA_CASES = {
    "I": (
        JointTopology.TOPO_I,
        Point(10, 0, 0),
        (Point(0, 0, 0), Point(10, 0, 0), "main", None),
        (Point(10, 0, 0), Point(20, 0, 0), "main", None),
    ),
    "L": (
        JointTopology.TOPO_L,
        Point(0, 0, 0),
        (Point(0, 0, 0), Point(10, 0, 0), "main", Vector(0, 1, 0)),
        (Point(0, 0, 0), Point(0, 10, 0), "main", Vector(1, 0, 0)),
    ),
    "T": (
        JointTopology.TOPO_T,
        Point(-5, 0, 0),
        (Point(-5, 0, 0), Point(5, 0, 0), "main", Vector(0, 1, 0)),
        (Point(-5, -2, 0), Point(-5, 8, 0), "cross", Vector(1, 0, 0)),
    ),
    "X": (
        JointTopology.TOPO_X,
        Point(0, 0, 0),
        (Point(-3, 0, 0), Point(7, 0, 0), "cross", Vector(0, 1, 0)),
        (Point(0, -2, 0), Point(0, 8, 0), "cross", Vector(1, 0, 0)),
    ),
}


def _assert_beam_info(topo_results, beam, joint_point, role, ref_side_normal):
    info = topo_results.info_for(beam)
    assert info.role == role
    if role == "main":
        expected_end = "start" if TOL.is_allclose(beam.centerline.start, joint_point) else "end"
        assert info.end == expected_end
    else:
        assert info.end is None
    assert TOL.is_close(info.location_parameter, distance_point_point(beam.centerline.start, joint_point))
    if ref_side_normal is None:
        assert info.ref_side_index is None
    else:
        assert TOL.is_allclose(beam.ref_sides[info.ref_side_index].normal, ref_side_normal)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("flip_a", [False, True])
@pytest.mark.parametrize("flip_b", [False, True])
@pytest.mark.parametrize("case", sorted(BEAM_METADATA_CASES))
def test_find_topology_beam_metadata(case, flip_a, flip_b, reverse):
    """Per-beam role, end, ref_side_index and location_parameter, for flipped beams and either input order."""
    expected_topology, joint_point, spec_a, spec_b = BEAM_METADATA_CASES[case]
    beam_a = Beam.from_endpoints(spec_a[0], spec_a[1], 1, 1)
    beam_b = Beam.from_endpoints(spec_b[0], spec_b[1], 1, 1)
    beam_a = flip_beam(beam_a) if flip_a else beam_a
    beam_b = flip_beam(beam_b) if flip_b else beam_b
    inputs = (beam_b, beam_a) if reverse else (beam_a, beam_b)

    topo_results = ConnectionSolver().find_topology(*inputs)

    assert topo_results.topology == expected_topology
    assert TOL.is_allclose(topo_results.location, joint_point)
    _assert_beam_info(topo_results, beam_a, joint_point, *spec_a[2:])
    _assert_beam_info(topo_results, beam_b, joint_point, *spec_b[2:])
    # main goes first whatever the input order; ties (L: main/main, X: cross/cross) keep the input order
    expected_order = (beam_a, beam_b) if case == "T" else inputs
    assert topo_results.get_element_by_role(*inputs) == expected_order


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
        main, other = topo_results.get_element_by_role(beam_a, beam_b)
        assert main is beam_a and other is beam_b, "Expected first beam ordered first in topology result"

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
        assert topo_results.info_for(plate_a).edge_index == expected_segments[0], f"Expected a_segment_index = {expected_segments[0]}"
        assert topo_results.info_for(plate_b).edge_index == expected_segments[1], f"Expected b_segment_index = {expected_segments[1]}"
    elif expected_topology == JointTopology.TOPO_EDGE_FACE:
        # get_element_by_role puts the edge plate first regardless of input order
        edge_plate, face_plate = topo_results.get_element_by_role(plate_a, plate_b)
        assert topo_results.info_for(edge_plate).edge_index == expected_segments[0], f"Expected a_segment_index = {expected_segments[0]}"
        assert topo_results.info_for(face_plate).edge_index == expected_segments[1], f"Expected b_segment_index = {expected_segments[1]}"


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


# --- per-plate locations ---------------------------------------------------------------------------
#
# The face plate is a 100 x 100 square extruded from z=0 down to z=-10 (its ref side 0 is the z=0 face).
# The edge plate stands upright at x=50, `gap` above that face, with its bottom edge running y=-50..50,
# so it lands on the face plate over y=0..50 only.


def _face_plate():
    return Plate.from_outline_thickness(Polyline([[0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0], [0, 0, 0]]), 10)


def _edge_on_face_plate(gap):
    outline = Polyline([[50, -50, gap], [50, 50, gap], [50, 50, gap + 100], [50, -50, gap + 100], [50, -50, gap]])
    return Plate.from_outline_thickness(outline, 10, vector=Vector(1, 0, 0))


def _edge_on_edge_plate(gap):
    """Upright plate whose bottom edge runs along the face plate's y=100 edge over x=50..250, `gap` above it.

    Its edge is twice as long as the face plate's, so the shared overlap sits at a different parameter on
    each edge, and mixing up which edge a location is measured on would show.
    """
    outline = Polyline([[50, 100, gap], [250, 100, gap], [250, 100, gap + 100], [50, 100, gap + 100], [50, 100, gap]])
    return Plate.from_outline_thickness(outline, 10, vector=Vector(0, 1, 0))


@pytest.mark.parametrize("reverse", [False, True])
def test_plate_edge_face_per_plate_locations(reverse):
    """Each plate's location lies on that plate: across a gap, the edge and face points differ."""
    face, edge = _face_plate(), _edge_on_face_plate(gap=2)
    inputs = (edge, face) if reverse else (face, edge)

    topo_info = PlateConnectionSolver().find_topology(*inputs, max_distance=5)

    assert topo_info.topology == JointTopology.TOPO_EDGE_FACE
    assert TOL.is_close(topo_info.distance, 2)
    # midpoint of the overlap y=0..50, on the edge (z=2) and on the face's ref side 0 (z=0)
    assert TOL.is_allclose(topo_info.info_for(edge).location, Point(50, 25, 2))
    assert TOL.is_allclose(topo_info.info_for(face).location, Point(50, 25, 0))
    assert TOL.is_allclose(topo_info.location, Point(50, 25, 1))
    assert topo_info.info_for(face).ref_side_index == 0


@pytest.mark.parametrize("reverse", [False, True])
def test_plate_edge_edge_per_plate_locations(reverse):
    """Each plate's location is the midpoint of the edges' overlap, measured on its own edge."""
    plate_a, plate_b = _face_plate(), _edge_on_edge_plate(gap=3)
    inputs = (plate_b, plate_a) if reverse else (plate_a, plate_b)

    topo_info = PlateConnectionSolver().find_topology(*inputs, max_distance=5)

    assert topo_info.topology == JointTopology.TOPO_EDGE_EDGE
    # the edges overlap over x=50..100
    assert TOL.is_allclose(topo_info.info_for(plate_a).location, Point(75, 100, 0))
    assert TOL.is_allclose(topo_info.info_for(plate_b).location, Point(75, 100, 3))
    assert TOL.is_allclose(topo_info.location, Point(75, 100, 1.5))


def test_plate_topology_unknown_when_apart():
    face, edge = _face_plate(), _edge_on_face_plate(gap=50)

    topo_info = PlateConnectionSolver().find_topology(face, edge, max_distance=5)

    assert topo_info.topology == JointTopology.TOPO_UNKNOWN
    assert topo_info.distance is None and topo_info.location is None
    for plate in (face, edge):
        assert all(value is None for value in topo_info.info_for(plate).__data__.values())


# --- update_location -------------------------------------------------------------------------------


def _l_beams():
    return Beam.from_endpoints(Point(0, 0, 0), Point(10, 0, 0), 1, 1), Beam.from_endpoints(Point(0, 0, 0), Point(0, 10, 0), 1, 1)


def test_beam_update_location_follows_moved_beam():
    beam_a, beam_b = _l_beams()
    solver = ConnectionSolver()
    topo_info = solver.find_topology(beam_a, beam_b)
    before = {beam: dict(topo_info.info_for(beam).__data__) for beam in (beam_a, beam_b)}

    # slide beam_b along beam_a and lift it, so the centerlines' closest points are (2, 0, 0) and (2, 0, 1)
    beam_b.transform(Translation.from_vector([2, 0, 1]))
    location = solver.update_location(beam_a, beam_b, topo_info)

    assert TOL.is_allclose(location, Point(2, 0, 0.5))
    assert TOL.is_allclose(topo_info.location, Point(2, 0, 0.5))
    assert TOL.is_close(topo_info.info_for(beam_a).location_parameter, 2)
    assert TOL.is_close(topo_info.info_for(beam_b).location_parameter, 0)
    # only the location changes; the rest of the solved topology is left as it was
    assert topo_info.topology == JointTopology.TOPO_L
    assert TOL.is_close(topo_info.distance, 0)
    for beam in (beam_a, beam_b):
        after = topo_info.info_for(beam).__data__
        assert {k: v for k, v in after.items() if k != "location_parameter"} == {k: v for k, v in before[beam].items() if k != "location_parameter"}


def test_beam_update_location_requires_both_beams():
    beam_a, beam_b = _l_beams()
    topo_info = ConnectionSolver().find_topology(beam_a, beam_b)
    stranger = Beam.from_endpoints(Point(0, 0, 0), Point(0, 0, 10), 1, 1)

    with pytest.raises(ValueError):
        ConnectionSolver().update_location(beam_a, stranger, topo_info)


@pytest.mark.parametrize("reverse", [False, True])
def test_plate_update_location_edge_face(reverse):
    """`reverse` passes the face plate first, so the face/edge roles are looked up rather than assumed."""
    face, edge = _face_plate(), _edge_on_face_plate(gap=2)
    solver = PlateConnectionSolver()
    topo_info = solver.find_topology(face, edge, max_distance=5)

    edge.transform(Translation.from_vector([0, 10, 0]))  # now lands on the face over y=0..60
    plates = (face, edge) if reverse else (edge, face)
    location = solver.update_location(*plates, topo_info)

    assert TOL.is_allclose(location, Point(50, 30, 1))
    assert TOL.is_allclose(topo_info.info_for(edge).location, Point(50, 30, 2))
    assert TOL.is_allclose(topo_info.info_for(face).location, Point(50, 30, 0))
    assert topo_info.topology == JointTopology.TOPO_EDGE_FACE


def test_plate_update_location_edge_edge():
    plate_a, plate_b = _face_plate(), _edge_on_edge_plate(gap=3)
    solver = PlateConnectionSolver()
    topo_info = solver.find_topology(plate_a, plate_b, max_distance=5)

    plate_b.transform(Translation.from_vector([10, 0, 0]))  # the edges now overlap over x=60..100
    location = solver.update_location(plate_a, plate_b, topo_info)

    assert TOL.is_allclose(location, Point(80, 100, 1.5))
    assert TOL.is_allclose(topo_info.info_for(plate_a).location, Point(80, 100, 0))
    assert TOL.is_allclose(topo_info.info_for(plate_b).location, Point(80, 100, 3))


@pytest.mark.parametrize(
    "make_moving_plate,shift",
    [
        (lambda: _edge_on_face_plate(gap=2), [0, 500, 0]),  # edge slid off the face
        (lambda: _edge_on_edge_plate(gap=3), [500, 0, 0]),  # edges no longer overlap
    ],
)
def test_plate_update_location_returns_none_when_no_longer_overlapping(make_moving_plate, shift):
    plate, moving = _face_plate(), make_moving_plate()
    solver = PlateConnectionSolver()
    topo_info = solver.find_topology(plate, moving, max_distance=5)
    before = topo_info.__data__

    moving.transform(Translation.from_vector(shift))

    assert solver.update_location(plate, moving, topo_info) is None
    assert topo_info.__data__ == before


def test_plate_update_location_unknown_topology_returns_none():
    plate_a, plate_b = _face_plate(), _edge_on_face_plate(gap=2)
    topo_info = TopologyInfo(JointTopology.TOPO_UNKNOWN, element_topo_info={str(plate_a.guid): PlateTopologyInfo(), str(plate_b.guid): PlateTopologyInfo()})

    assert PlateConnectionSolver().update_location(plate_a, plate_b, topo_info) is None
    assert topo_info.location is None


def test_plate_update_location_requires_both_plates():
    face, edge = _face_plate(), _edge_on_face_plate(gap=2)
    topo_info = PlateConnectionSolver().find_topology(face, edge, max_distance=5)

    with pytest.raises(ValueError):
        PlateConnectionSolver().update_location(face, _face_plate(), topo_info)
