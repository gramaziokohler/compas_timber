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
    line = Line(Point(x=5.53733031674, y=12.3190045249, z=0.0), Point(x=20.8427601810, y=12.3190045249, z=0.0))
    plane = Plane(point=Point(x=15.436, y=16.546, z=-2.703), normal=Vector(x=-0.957, y=-0.289, z=0.000))

    expected_point = Point(x=16.7100478890, y=12.3190045249, z=0.0)
    expected_t = 0.72998391233079618

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
