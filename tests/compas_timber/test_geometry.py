import math

import pytest
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_brep import Brep

from compas_timber.geometry import brep_difference_first
from compas_timber.geometry import brep_edge_indices_not_parallel_to_plane
from compas_timber.geometry import brep_from_box_with_rounded_corners
from compas_timber.geometry import brep_from_outlines
from compas_timber.geometry import brep_intersection_first
from compas_timber.geometry import brep_union_first


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


@pytest.mark.requires_occ
def test_brep_from_outlines_outline_a_below_outline_b():
    outline_a = _rectangle(z=0)
    outline_b = _rectangle(z=1)

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


@pytest.mark.requires_occ
def test_brep_from_outlines_outline_a_above_outline_b():
    # outline_a is physically above outline_b even though it's passed first
    outline_a = _rectangle(z=1)
    outline_b = _rectangle(z=0)

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


@pytest.mark.requires_occ
def test_brep_from_outlines_mismatched_winding_direction():
    # outline_a wound clockwise, outline_b wound counter-clockwise (viewed from +Z)
    outline_a = Polyline([Point(0, 0, 0), Point(0, 5, 0), Point(10, 5, 0), Point(10, 0, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 1), Point(0, 5, 1), Point(0, 0, 1)])

    brep = brep_from_outlines(outline_a, outline_b)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


@pytest.mark.requires_occ
def test_brep_from_outlines_triangular_profile():
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(0, 6, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 2), Point(10, 0, 2), Point(0, 6, 2), Point(0, 0, 2)])

    brep = brep_from_outlines(outline_a, outline_b)

    triangle_area = 0.5 * 10 * 6
    _assert_valid_solid(brep, expected_volume=triangle_area * 2)


@pytest.mark.requires_occ
def test_brep_from_outlines_convex_pentagon_profile():
    points = [(0, 0), (4, 0), (6, 3), (2, 6), (-2, 3)]
    outline_a = Polyline([Point(x, y, 0) for x, y in points] + [Point(*points[0], 0)])
    outline_b = Polyline([Point(x, y, 0.5) for x, y in points] + [Point(*points[0], 0.5)])

    brep = brep_from_outlines(outline_a, outline_b)

    pentagon_area = Polygon([Point(x, y, 0) for x, y in points]).area
    _assert_valid_solid(brep, expected_volume=pentagon_area * 0.5)


@pytest.mark.requires_occ
def test_brep_from_outlines_non_convex_l_shape_profile():
    points = [(0, 0), (6, 0), (6, 3), (3, 3), (3, 6), (0, 6)]
    outline_a = Polyline([Point(x, y, 0) for x, y in points] + [Point(*points[0], 0)])
    outline_b = Polyline([Point(x, y, 1.5) for x, y in points] + [Point(*points[0], 1.5)])

    brep = brep_from_outlines(outline_a, outline_b)

    l_shape_area = Polygon([Point(x, y, 0) for x, y in points]).area
    _assert_valid_solid(brep, expected_volume=l_shape_area * 1.5)


@pytest.mark.requires_occ
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


@pytest.mark.requires_occ
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


@pytest.mark.requires_occ
def test_brep_from_outlines_with_negative_z_normal():
    # explicit normal pointing opposite to world Z: outline_a (z=0) is "below" in world
    # terms but "above" relative to the given (0, 0, -1) normal.
    outline_a = _rectangle(z=0)
    outline_b = _rectangle(z=1)
    normal = Vector(0, 0, -1)

    brep = brep_from_outlines(outline_a, outline_b, normal=normal)

    _assert_valid_solid(brep, expected_volume=10 * 5 * 1)


@pytest.mark.requires_occ
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


def test_brep_from_outlines_raises_if_an_outline_is_not_planar():
    outline_a = _rectangle(z=0)
    # outline_b's corners do not lie in one plane
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 2), Point(0, 5, 0), Point(0, 0, 1)])

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)


@pytest.mark.requires_occ
def test_brep_from_outlines_with_a_tilted_outline():
    # a box 10 x 5, cut by a plane rising from z = 1 to z = 3 along x: the bottom of a DualContour need not be parallel
    outline_a = _rectangle(z=0)
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 3), Point(10, 5, 3), Point(0, 5, 1), Point(0, 0, 1)])

    brep = brep_from_outlines(outline_a, outline_b)

    assert brep.is_solid
    assert abs(brep.volume) == pytest.approx(10 * 5 * 2)


@pytest.mark.requires_occ
def test_brep_from_outlines_with_a_tilted_outline_rounded_as_in_a_btlx_file():
    # BTLx stores coordinates to three decimals, which leaves an outline on a tilted plane a little off it
    corners = [(50.0 * math.cos(math.pi * i / 6), 50.0 * math.sin(math.pi * i / 6)) for i in range(12)]
    outline_a = Polyline([Point(x, y, 0) for x, y in corners] + [Point(corners[0][0], corners[0][1], 0)])
    tilted = [Point(round(x, 3), round(y, 3), round(20.0 + 0.3713 * x + 0.1291 * y, 3)) for x, y in corners]
    outline_b = Polyline(tilted + [tilted[0]])

    brep = brep_from_outlines(outline_a, outline_b)

    assert brep.is_solid
    area = 6 * 50.0**2 * math.sin(math.pi / 6)  # of the regular dodecagon, whose centroid is at the origin
    assert abs(brep.volume) == pytest.approx(area * 20.0, rel=1e-4)


def test_brep_from_outlines_raises_if_outlines_are_square_to_each_other():
    outline_a = _rectangle(z=0)
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 0, 6), Point(0, 0, 6), Point(0, 0, 1)])

    with pytest.raises(ValueError):
        brep_from_outlines(outline_a, outline_b)


def _box_brep(xsize, ysize, zsize, point=None):
    return Brep.from_box(Box(xsize, ysize, zsize, frame=Frame(point or Point(0, 0, 0))))


@pytest.mark.requires_occ
def test_brep_difference_first_returns_a_single_solid():
    box = _box_brep(10, 10, 10)
    cutter = _box_brep(2, 2, 20)

    result = brep_difference_first(box, cutter)

    _assert_valid_solid(result, expected_volume=10 * 10 * 10 - 2 * 2 * 10)


@pytest.mark.requires_occ
def test_brep_difference_first_returns_one_piece_when_subtraction_splits():
    box = _box_brep(10, 10, 10)
    slab = _box_brep(2, 20, 20)  # cuts the box into two disconnected halves

    result = brep_difference_first(box, slab)

    # both halves are the same size, whichever is returned it is a single solid, not a list
    _assert_valid_solid(result, expected_volume=4 * 10 * 10)


@pytest.mark.requires_occ
def test_brep_difference_first_raises_when_nothing_is_left():
    box = _box_brep(10, 10, 10)
    cutter = _box_brep(20, 20, 20)

    with pytest.raises(IndexError):
        brep_difference_first(box, cutter)


@pytest.mark.requires_occ
def test_brep_union_first_returns_a_single_solid():
    box_a = _box_brep(10, 10, 10)
    box_b = _box_brep(10, 10, 10, point=Point(5, 0, 0))

    result = brep_union_first(box_a, box_b)

    _assert_valid_solid(result, expected_volume=15 * 10 * 10)


@pytest.mark.requires_occ
def test_brep_union_first_accepts_more_than_two_breps():
    box_a = _box_brep(10, 10, 10)
    box_b = _box_brep(10, 10, 10, point=Point(5, 0, 0))
    box_c = _box_brep(10, 10, 10, point=Point(10, 0, 0))

    result = brep_union_first(box_a, box_b, box_c)

    _assert_valid_solid(result, expected_volume=20 * 10 * 10)


def test_brep_union_first_requires_something_to_union_with():
    with pytest.raises(ValueError):
        brep_union_first(object())


@pytest.mark.requires_occ
def test_brep_intersection_first_returns_a_single_solid():
    box_a = _box_brep(10, 10, 10)
    box_b = _box_brep(10, 10, 10, point=Point(5, 0, 0))

    result = brep_intersection_first(box_a, box_b)

    _assert_valid_solid(result, expected_volume=5 * 10 * 10)


@pytest.mark.requires_occ
def test_brep_intersection_first_raises_when_breps_do_not_overlap():
    box_a = _box_brep(10, 10, 10)
    box_b = _box_brep(10, 10, 10, point=Point(50, 0, 0))

    with pytest.raises(IndexError):
        brep_intersection_first(box_a, box_b)


def _tilted_frame():
    return Frame(Point(10, 20, 30), Vector(1, 1, 0), Vector(-1, 1, 1))


@pytest.mark.requires_occ
def test_brep_edge_indices_not_parallel_to_plane_selects_the_edges_along_the_box_height():
    frame = _tilted_frame()
    brep = Brep.from_box(Box(10, 20, 30, frame))

    indices = brep_edge_indices_not_parallel_to_plane(brep, Plane.from_frame(frame))

    assert len(indices) == 4
    for index in indices:
        edge = brep.edges[index]
        direction = Vector.from_start_end(edge.start_vertex.point, edge.end_vertex.point)
        assert TOL.is_close(abs(direction.dot(frame.zaxis)), 30.0)


@pytest.mark.requires_occ
def test_brep_from_box_with_rounded_corners_fillets_the_corners():
    box = Box(80, 160, 50, _tilted_frame())

    brep = brep_from_box_with_rounded_corners(box, 20)

    _assert_rounded_box(brep, box, expected_volume=(80 * 160 - (4 - math.pi) * 20**2) * 50)


@pytest.mark.requires_occ
@pytest.mark.parametrize("xsize, ysize", [(80, 160), (160, 80), (80, 80)])
def test_brep_from_box_with_rounded_corners_where_the_corners_meet(xsize, ysize):
    # a radius of half the smaller side leaves no flat side between the corners to fillet, e.g. a round tenon
    box = Box(xsize, ysize, 50, _tilted_frame())

    brep = brep_from_box_with_rounded_corners(box, 40)

    _assert_rounded_box(brep, box, expected_volume=((max(xsize, ysize) - 80) * 80 + math.pi * 40**2) * 50)


def _assert_rounded_box(brep, box, expected_volume):
    # not `_assert_valid_solid`: `Brep.is_closed` only counts faces, and a cylinder has three
    assert brep.is_solid
    assert brep.is_valid
    assert TOL.is_close(brep.volume, expected_volume)
    # the rounded box lies within the box
    assert TOL.is_close(brep_intersection_first(brep, Brep.from_box(box)).volume, brep.volume)


def test_brep_from_box_with_rounded_corners_raises_if_radius_is_too_large():
    with pytest.raises(ValueError):
        brep_from_box_with_rounded_corners(Box(80, 160, 50), 41)


@pytest.mark.requires_occ
def test_brep_from_outlines_with_a_repeated_point():
    # a 10 x 10 x 5 box, whose top outline has a point halfway along one side where the bottom one repeats a corner:
    # the side face there is a triangle and a quad instead of two quads
    outline_a = Polyline([Point(0, 0, 5), Point(10, 0, 5), Point(10, 5, 5), Point(10, 10, 5), Point(0, 10, 5), Point(0, 0, 5)])
    outline_b = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0), Point(10, 10, 0), Point(0, 10, 0), Point(0, 0, 0)])

    brep = brep_from_outlines(outline_a, outline_b)

    assert brep.volume == pytest.approx(500.0)
