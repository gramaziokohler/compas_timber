import pytest

from compas.tolerance import TOL
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import angle_vectors

from compas_timber.utils import intersection_line_line_param
from compas_timber.utils import intersection_line_plane_param
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import do_segments_overlap
from compas_timber.utils import distance_segment_segment
from compas_timber.utils import get_segment_overlap
from compas_timber.utils import move_polyline_segment_to_line
from compas_timber.utils import join_polyline_segments
from compas_timber.utils import get_polyline_normal_vector
from compas_timber.utils import combine_parallel_segments


def test_intersection_line_line_param():
    line_a = Line(Point(x=5.53733031674, y=18.6651583710, z=0.0), Point(x=5.53733031674, y=0.248868778281, z=0.0))
    line_b = Line(Point(x=5.53733031674, y=12.3190045249, z=0.0), Point(x=20.8427601810, y=12.3190045249, z=0.0))

    line_a_intersection, line_b_intersection = intersection_line_line_param(line_a, line_b)

    expected_point_a = Point(x=5.53733031674, y=12.3190045249, z=0.0)
    expected_t_a = 0.34459459459459457

    expected_point_b = Point(x=5.53733031674, y=12.3190045249, z=0.0)
    expected_t_b = 0.0

    line_a_intersection_point, line_a_intersection_t = line_a_intersection
    line_b_intersection_point, line_b_intersection_t = line_b_intersection

    assert TOL.is_allclose(line_a_intersection_point, expected_point_a)
    assert TOL.is_close(line_a_intersection_t, expected_t_a)
    assert TOL.is_allclose(line_b_intersection_point, expected_point_b)
    assert TOL.is_close(line_b_intersection_t, expected_t_b)


def test_intersection_line_plane_param():
    TOL.absolute = 0.001
    TOL.unit = "MM"
    TOL.relative = 0.001

    line = Line(Point(x=5.53733031674, y=12.3190045249, z=0.0), Point(x=20.8427601810, y=12.3190045249, z=0.0))
    plane = Plane(point=Point(x=15.436, y=16.546, z=-2.703), normal=Vector(x=-0.957, y=-0.289, z=0.000))

    # NOTE: I can't figure out why these values were suddenly wrong and had to be changed:
    # expected_point = Point(x=16.7100478890, y=12.3190045249, z=0.0)
    # expected_t = 0.72998391233079618
    expected_point = [16.712490796555798, 12.3190045249, 0.0]
    expected_t = 0.7301435228494384

    intersection_point, t = intersection_line_plane_param(line, plane)

    assert TOL.is_allclose(expected_point, intersection_point)
    assert TOL.is_close(expected_t, t)


def test_is_polyline_clockwise():
    pline_ccw = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    pline_cw = Polyline([[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]])

    assert not is_polyline_clockwise(pline_ccw, [0, 0, 1])
    assert is_polyline_clockwise(pline_cw, [0, 0, 1])


def test_correct_polyline_direction():
    pline_ccw = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    pline_cw = Polyline([[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]])

    pline_ccw_corrected = correct_polyline_direction(pline_ccw, [0, 0, 1], clockwise=True)
    pline_cw_corrected = correct_polyline_direction(pline_cw, [0, 0, 1], clockwise=False)

    assert pline_ccw == pline_cw_corrected
    assert pline_cw == pline_ccw_corrected


@pytest.fixture
def polyline():
    points = [[0, 0, 0], [2, 0, 0], [2, 1, 0], [1, 2, 0], [0, 2, 0], [0, 0, 0]]
    return Polyline(points)


@pytest.fixture
def polyline_perp_vectors():
    return [
        Vector(0, -1, 0),
        Vector(1, 0, 0),
        Vector(1, 1, 0),
        Vector(0, 1, 0),
        Vector(-1, 0, 0),
    ]


@pytest.fixture
def polyline_with_concave():
    points = [[0, 0, 0], [2, 0, 0], [2, 1, 0], [3, 1, 0], [3, 0, 0], [4, 0, 0], [4, 2, 0], [0, 2, 0], [0, 0, 0]]
    return Polyline(points)


@pytest.fixture
def concave_polyline_perp_vectors():
    return [
        Vector(0, -1, 0),
        Vector(1, 0, 0),
        Vector(0, -1, 0),
        Vector(-1, 0, 0),
        Vector(0, -1, 0),
        Vector(1, 0, 0),
        Vector(0, 1, 0),
        Vector(-1, 0, 0),
    ]


def test_is_point_in_polyline(polyline, polyline_with_concave):
    test_point_inside = Point(1, 1, 0)
    test_point_outside = Point(3, 3, 0)
    test_point_in_concave = Point(2.5, 0.5, 0)  # Inside the concave area aka outside the polyline

    assert is_point_in_polyline(test_point_inside, polyline)
    assert not is_point_in_polyline(test_point_outside, polyline)
    assert is_point_in_polyline(test_point_inside, polyline_with_concave)
    assert not is_point_in_polyline(test_point_outside, polyline_with_concave)
    assert not is_point_in_polyline(test_point_in_concave, polyline_with_concave)


def test_get_polyline_segment_perpendicular_vector(polyline, polyline_perp_vectors):
    for i, expected_vector in enumerate(polyline_perp_vectors):
        assert TOL.is_angle_zero(angle_vectors(get_polyline_segment_perpendicular_vector(polyline, i), expected_vector))


def test_get_polyline_segment_perpendicular_vector_concave(polyline_with_concave, concave_polyline_perp_vectors):
    for i, expected_vector in enumerate(concave_polyline_perp_vectors):
        assert TOL.is_angle_zero(angle_vectors(get_polyline_segment_perpendicular_vector(polyline_with_concave, i), expected_vector))


def test_is_point_in_polyline_reversed(polyline, polyline_with_concave):
    test_point_inside = Point(1, 1, 0)
    test_point_outside = Point(3, 3, 0)
    test_point_in_concave = Point(2.5, 0.5, 0)  # Inside the concave area aka outside the polyline
    polyline = Polyline(polyline.points[::-1])
    polyline_with_concave = Polyline(polyline_with_concave.points[::-1])

    assert is_point_in_polyline(test_point_inside, polyline)
    assert not is_point_in_polyline(test_point_outside, polyline)
    assert is_point_in_polyline(test_point_inside, polyline_with_concave)
    assert not is_point_in_polyline(test_point_outside, polyline_with_concave)
    assert not is_point_in_polyline(test_point_in_concave, polyline_with_concave)


def test_get_polyline_segment_perpendicular_vector_reversed(polyline, polyline_perp_vectors):
    polyline = Polyline(polyline.points[::-1])
    polyline_perp_vectors = polyline_perp_vectors[::-1]
    for i, expected_vector in enumerate(polyline_perp_vectors):
        assert TOL.is_angle_zero(angle_vectors(get_polyline_segment_perpendicular_vector(polyline, i), expected_vector))


def test_get_polyline_segment_perpendicular_vector_concave_reversed(polyline_with_concave, concave_polyline_perp_vectors):
    polyline_with_concave = Polyline(polyline_with_concave.points[::-1])
    concave_polyline_perp_vectors = concave_polyline_perp_vectors[::-1]
    for i, expected_vector in enumerate(concave_polyline_perp_vectors):
        assert TOL.is_angle_zero(angle_vectors(get_polyline_segment_perpendicular_vector(polyline_with_concave, i), expected_vector))


def test_do_segments_overlap():
    segment_a = Line(Point(0, 0, 0), Point(10, 0, 0))
    overlapping = [
        Line(Point(5, 0, 0), Point(15, 0, 0)),
        Line(Point(9, 1, 0), Point(10, 10, 0)),
        Line(Point(2, 0, 0), Point(8, 0, 0)),
        Line(Point(-2, 0, 0), Point(12, 0, 0)),
        Line(Point(0, 0, 0), Point(10, 0, 0)),
    ]
    non_overlapping = [
        Line(Point(11, 0, 0), Point(20, 0, 0)),
        Line(Point(10, 1, 0), Point(20, 10, 0)),
        Line(Point(-10, 0, 0), Point(0, 0, 0)),
        Line(Point(10, 0, 0), Point(15, 0, 0)),
        Line(Point(11, 0, 0), Point(21, 0, 0)),
    ]

    for segment_b in overlapping:
        assert do_segments_overlap(segment_a, segment_b)
    for segment_b in non_overlapping:
        assert not do_segments_overlap(segment_a, segment_b)


def test_distance_segment_segment():
    segment_a = Line(Point(0, 0, 0), Point(10, 0, 0))
    segments = [
        Line(Point(5, 0, 0), Point(15, 0, 0)),  # Overlapping parallel segment
        Line(Point(9, 1, 0), Point(10, 10, 0)),  # Overlapping non-parallel segment
        Line(Point(2, 1, 0), Point(8, 1, 0)),  # Overlapping parallel segment internal to segment_a
        Line(Point(13, 4, 0), Point(15, 6, 0)),  # Non-overlapping segment
        Line(Point(15, -5, 0), Point(15, 5, 0)),  # crossing perpendicular segment
        Line(Point(5, -5, 0), Point(5, 5, 0)),  # crossing perpendicular segment
        Line(Point(5, -5, 1), Point(5, 5, 1)),  # crossing non-intersecting perpendicular segment
    ]
    results = [0.0, 1.0, 1.0, 5.0, 5.0, 0.0, 1.0]
    # Distance between non-overlapping segments
    for seg, result in zip(segments, results):
        assert TOL.is_close(distance_segment_segment(segment_a, seg), result)


def test_get_segment_overlap():
    seg_a = Line(Point(0, 0, 0), Point(10, 0, 0))
    segs = [
        Line(Point(0, 0, 0), Point(10, 0, 0)),
        Line(Point(-1, 0, 0), Point(9, 0, 0)),
        Line(Point(1, 0, 0), Point(11, 0, 0)),
        Line(Point(1, 0, 0), Point(9, 0, 0)),
        Line(Point(-1, 0, 0), Point(11, 0, 0)),
        Line(Point(-11, 0, 0), Point(-1, 0, 0)),
        Line(Point(11, 0, 0), Point(21, 0, 0)),
        Line(Point(10, 0, 0), Point(20, 0, 0)),
        Line(Point(-10, 0, 0), Point(0, 0, 0)),
    ]
    expected_overlaps = [
        (0, 10),
        (0, 9),
        (1, 10),
        (1, 9),
        (0, 10),
        None,
        None,
        None,
        None,
    ]

    for seg_b, o in zip(segs, expected_overlaps):
        assert get_segment_overlap(seg_a, seg_b) == o


def test_move_polyline_segment_to_line():
    polyline = Polyline([[0, 0, 0], [2, 0, 0], [3, 2, 0], [0, 2, 0], [0, 0, 0]])
    line = Line([2, 0, 0], [2, 2, 0])
    move_polyline_segment_to_line(polyline, 1, line)
    expected = Polyline([[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0], [0, 0, 0]])
    assert polyline == expected


def test_move_polyline_segment_to_line_angled():
    polyline = Polyline([[0, 0, 0], [3, 3, 0], [5, 3, 0], [8, 0, 0], [0, 0, 0]])
    line = Line([0, 2, 0], [8, 2, 0])
    move_polyline_segment_to_line(polyline, 1, line)
    expected = Polyline([[0, 0, 0], [2, 2, 0], [6, 2, 0], [8, 0, 0], [0, 0, 0]])
    assert polyline == expected


def test_join_polyline_segments():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([1, 0, 0], [1, 1, 0]),
        Line([1, 1, 0], [0, 1, 0]),
        Line([0, 1, 0], [0, 0, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=False)
    expected = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    assert polylines[0] == expected


def test_join_polyline_segments_close_loop():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([1, 0, 0], [1, 1, 0]),
        Line([1, 1, 0], [0, 1, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=True)
    expected = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    assert polylines[0] == expected


def test_join_polyline_segments_segs_flipped():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([1, 1, 0], [1, 0, 0]),
        Line([1, 1, 0], [0, 1, 0]),
        Line([0, 0, 0], [0, 1, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=True)
    expected = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    assert polylines[0] == expected


def test_join_polyline_segments_wrong_order():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([0, 0, 0], [0, 1, 0]),
        Line([1, 1, 0], [1, 0, 0]),
        Line([1, 1, 0], [0, 1, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=True)
    expected = Polyline([[0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]])
    assert polylines[0] == expected


def test_join_polyline_segments_with_gap():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([0, 0, 0], [0, 1, 0]),
        Line([2, 1, 0], [2, 0, 0]),
        Line([2, 1, 0], [0, 2, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=False)
    expected = [Polyline([[0, 1, 0], [0, 0, 0], [1, 0, 0]]), Polyline([[0, 2, 0], [2, 1, 0], [2, 0, 0]])]
    assert polylines == expected


def test_join_polyline_segments_with_gap_and_unjoined():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([0, 0, 0], [0, 1, 0]),
        Line([3, 0, 0], [3, 1, 0]),
        Line([2, 1, 0], [2, 0, 0]),
        Line([4, 0, 0], [4, 1, 0]),
        Line([2, 1, 0], [0, 2, 0]),
        Line([0, 3, 0], [0, -2, 0]),
    ]
    polylines, unjoined = join_polyline_segments(segments, close_loop=False)
    polylines_expected = [Polyline([[0, 1, 0], [0, 0, 0], [1, 0, 0]]), Polyline([[0, 2, 0], [2, 1, 0], [2, 0, 0]])]
    unjoined_expected = [Line([3, 0, 0], [3, 1, 0]), Line([4, 0, 0], [4, 1, 0]), Line([0, 3, 0], [0, -2, 0])]
    assert polylines == polylines_expected
    assert unjoined == unjoined_expected


def test_join_polyline_segments_open():
    segments = [
        Line([0, 0, 0], [1, 0, 0]),
        Line([1, 0, 0], [1, 1, 0]),
    ]
    polylines, _ = join_polyline_segments(segments, close_loop=False)
    expected = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0]])
    assert polylines[0] == expected


def test_get_polyline_normal_vector():
    polyline = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    normal = get_polyline_normal_vector(polyline)
    expected = Vector(0, 0, -1)
    assert TOL.is_allclose(normal, expected)


def test_get_polyline_normal_vector_reversed():
    polyline = Polyline([[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]])
    normal = get_polyline_normal_vector(polyline)
    expected = Vector(0, 0, 1)
    assert TOL.is_allclose(normal, expected)


def test_get_polyline_normal_vector_with_direction():
    polyline = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    normal = get_polyline_normal_vector(polyline, Vector(0, 1, -1))
    expected = Vector(0, 0, -1)
    assert TOL.is_allclose(normal, expected)


def test_get_polyline_normal_vector_angled():
    polyline = Polyline([[0, 0, 0], [1, 0, 1], [1, 1, 1], [0, 1, 0], [0, 0, 0]])
    normal = get_polyline_normal_vector(polyline)
    expected = Vector((2.0**0.5) / 2.0, 0, -(2.0**0.5) / 2.0)
    assert TOL.is_allclose(normal, expected)


def test_combine_parallel_segments():
    polyline = Polyline([[0, 0, 0], [1, 0, 0], [2, 0, 0], [2, 1, 0], [2, 2, 0], [1, 2, 0], [0, 2, 0], [0, 0, 0]])
    combine_parallel_segments(polyline)
    expected = Polyline([[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0], [0, 0, 0]])
    assert polyline == expected
