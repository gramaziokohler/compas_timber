import pytest
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.geometry import brep_from_outlines


def _rectangle(z, width=10, height=5):
    return Polyline(
        [
            Point(0, 0, z),
            Point(width, 0, z),
            Point(width, height, z),
            Point(0, height, z),
            Point(0, 0, z),
        ]
    )


def _assert_valid_solid(brep, expected_volume):
    assert brep.is_solid
    assert brep.is_closed
    assert brep.volume > 0
    assert TOL.is_close(brep.volume, expected_volume)


def test_brep_from_outlines_outline_a_below_outline_b():
    outline_a = _rectangle(z=0)
    outline_b = _rectangle(z=1)

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


def test_brep_from_outlines_outline_a_above_outline_b():
    # outline_a is physically above outline_b even though it's passed first
    outline_a = _rectangle(z=1)
    outline_b = _rectangle(z=0)

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


def test_brep_from_outlines_mismatched_winding_direction():
    # outline_a wound clockwise, outline_b wound counter-clockwise (viewed from +Z)
    outline_a = Polyline([Point(0, 0, 0), Point(0, 5, 0), Point(10, 5, 0), Point(10, 0, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 1), Point(0, 5, 1), Point(0, 0, 1)])

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


def test_brep_from_outlines_triangular_profile():
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(0, 6, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 2), Point(10, 0, 2), Point(0, 6, 2), Point(0, 0, 2)])

    brep = brep_from_outlines(outline_a, outline_b)

    triangle_area = 0.5 * 10 * 6
    _assert_valid_solid(brep, expected_volume=triangle_area * 2)


def test_brep_from_outlines_convex_pentagon_profile():
    points = [(0, 0), (4, 0), (6, 3), (2, 6), (-2, 3)]
    outline_a = Polyline([Point(x, y, 0) for x, y in points] + [Point(*points[0], 0)])
    outline_b = Polyline([Point(x, y, 0.5) for x, y in points] + [Point(*points[0], 0.5)])

    brep = brep_from_outlines(outline_a, outline_b)

    pentagon_area = Polygon([Point(x, y, 0) for x, y in points]).area
    _assert_valid_solid(brep, expected_volume=pentagon_area * 0.5)


def test_brep_from_outlines_non_convex_l_shape_profile():
    points = [(0, 0), (6, 0), (6, 3), (3, 3), (3, 6), (0, 6)]
    outline_a = Polyline([Point(x, y, 0) for x, y in points] + [Point(*points[0], 0)])
    outline_b = Polyline([Point(x, y, 1.5) for x, y in points] + [Point(*points[0], 1.5)])

    brep = brep_from_outlines(outline_a, outline_b)

    l_shape_area = Polygon([Point(x, y, 0) for x, y in points]).area
    _assert_valid_solid(brep, expected_volume=l_shape_area * 1.5)


def test_brep_from_outlines_not_parallel_to_world_xy():
    # profile lives in a tilted plane, offset along its own (non world-Z) normal
    normal = Vector(1, 1, 1).unitized()
    frame = Frame.from_plane(Plane(Point(0, 0, 0), normal))
    local_points = [(0, 0, 0), (10, 0, 0), (10, 5, 0), (0, 5, 0)]

    points_a = [frame.to_world_coordinates(Point(*p)) for p in local_points]
    points_a.append(points_a[0])
    outline_a = Polyline(points_a)

    offset = normal * 2
    outline_b = Polyline([p + offset for p in points_a])

    brep = brep_from_outlines(outline_a, outline_b, normal=normal)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 2)


def test_brep_from_outlines_not_parallel_to_world_xy_outline_a_above_outline_b():
    normal = Vector(1, 1, 1).unitized()
    frame = Frame.from_plane(Plane(Point(0, 0, 0), normal))
    local_points = [(0, 0, 0), (10, 0, 0), (10, 5, 0), (0, 5, 0)]

    points_b = [frame.to_world_coordinates(Point(*p)) for p in local_points]
    points_b.append(points_b[0])
    outline_b = Polyline(points_b)

    offset = normal * 2
    outline_a = Polyline([p + offset for p in points_b])  # outline_a is above outline_b along normal

    brep = brep_from_outlines(outline_a, outline_b, normal=normal)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 2)


def test_brep_from_outlines_with_negative_z_normal():
    # explicit normal pointing opposite to world Z: outline_a (z=0) is "below" in world
    # terms but "above" relative to the given (0, 0, -1) normal.
    outline_a = _rectangle(z=0)
    outline_b = _rectangle(z=1)
    normal = Vector(0, 0, -1)

    brep = brep_from_outlines(outline_a, outline_b, normal=normal)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


def test_brep_from_outlines_default_normal_is_world_z():
    outline_a = _rectangle(z=0)
    outline_b = _rectangle(z=1)

    brep_default = brep_from_outlines(outline_a, outline_b)
    brep_explicit = brep_from_outlines(outline_a, outline_b, normal=Vector(0, 0, 1))

    assert TOL.is_close(brep_default.volume, brep_explicit.volume)


def test_brep_from_outlines_raises_if_outline_a_not_closed():
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 5, 0), Point(0, 5, 0)])  # not closed
    outline_b = _rectangle(z=1)

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)


def test_brep_from_outlines_raises_if_outline_b_not_closed():
    outline_a = _rectangle(z=0)
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 1), Point(0, 5, 1)])  # not closed

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)


def test_brep_from_outlines_raises_on_mismatched_vertex_count():
    outline_a = _rectangle(z=0)  # 4 unique vertices
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(5, 5, 1), Point(0, 0, 1)])  # 3 unique vertices

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)


def test_brep_from_outlines_raises_if_outlines_not_parallel():
    outline_a = _rectangle(z=0)
    # outline_b is tilted relative to outline_a's plane, not just offset along Z
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 2), Point(0, 5, 0), Point(0, 0, 1)])

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)
