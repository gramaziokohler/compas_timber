import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector

from compas.tolerance import TOL

from compas_timber.elements import Plate

from brep_mocks import make_plate_brep
from brep_mocks import make_single_face_brep


def test_flat_plate_creation():
    # this outline's point order triggers the frame flip in `PlateGeometry.from_global_outlines` (see
    # test_plate_frame). Local x stays aligned with outline_a[0]->outline_a[1] = (0, 20, 0), so `length`
    # (the extent along local x) now tracks the 20-long edge and `width` the 10-long edge.
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [([0, 0, 0], [-1, 0, 0]), ([0, 20, 0], [0, 1, 0]), ([10, 20, 0], [1, 0, 0]), ([10, 0, 0], [0, -1, 0])]
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert plate_a.thickness == 1, "Expected plate thickness to match input thickness"
    assert plate_a.length == 20, "Expected plate length to be 20"
    assert plate_a.width == 10, "Expected plate width to be 10"
    assert TOL.is_allclose(plate_a.normal, [0, 0, 1]), "Expected the normal to be the world Z-axis"
    for expected, plane in zip(expected_edge_planes, plate_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    # compare as sets: the OBB's local frame is rotated 90 degrees vs. before the fix, so `Box.points`
    # visits the same 8 corners in a different order.
    obb_points = {tuple(round(c, 6) for c in pt) for pt in plate_a.obb.points}
    expected_points = {tuple(round(c, 6) for c in pt) for pt in Box.from_points([Point(0, 0, 0), Point(10, 20, 1)]).points}
    assert obb_points == expected_points


def test_sloped_plate_creation():
    # this outline also triggers the frame flip (see test_plate_frame). Local x stays aligned with
    # outline_a[0]->outline_a[1] = (10, 0, 0), so `length` now tracks that 10-long edge, extended by the
    # slope to 20, and `width` tracks the 10*sqrt(2) diagonal edge; the frame origin and OBB rotate to match.
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [
        ([0, 10, 0], [0, -0.707106781, -0.707106781]),
        ([10, 10, 0], [0.81649658, -0.40824829, -0.40824829]),
        ([20, 20, 10], [0, 0.707106781, 0.707106781]),
        ([0, 20, 10], [-1, 0, 0]),
    ]

    expected_obb = Box(
        xsize=20.0,
        ysize=14.142135623730951,
        zsize=1.0,
        frame=Frame(
            point=Point(x=10.0, y=15.353553390593273, z=4.646446609406729), xaxis=Vector(x=-1.0, y=0.0, z=0.0), yaxis=Vector(x=0.0, y=0.7071067811865475, z=0.7071067811865476)
        ),
    )

    assert plate_a.frame.point == Point(20, 10, 0), "Expected plate frame to match input polyline"
    assert all([TOL.is_allclose(plate_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert TOL.is_close(plate_a.thickness, 1), "Expected plate thickness to match input thickness"
    assert TOL.is_close(plate_a.length, 20), "Expected plate length to be 20"
    assert TOL.is_close(plate_a.width, 14.1421356237), "Expected plate width to be 10*sqrt(2)"
    assert TOL.is_allclose(plate_a.normal, [0, 0.707106781, -0.707106781]), "Expected the normal to be at 45 degrees"
    for expected, plane in zip(expected_edge_planes, plate_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    assert TOL.is_allclose(expected_obb.frame.point, plate_a.obb.frame.point)
    assert TOL.is_allclose(expected_obb.frame.xaxis, plate_a.obb.frame.xaxis)
    assert TOL.is_allclose(expected_obb.frame.yaxis, plate_a.obb.frame.yaxis)
    assert TOL.is_close(expected_obb.xsize, plate_a.obb.xsize)
    assert TOL.is_close(expected_obb.ysize, plate_a.obb.ysize)
    assert TOL.is_close(plate_a.obb.zsize, 1.0)


def test_plate_frame():
    # this polyline winds clockwise around +Z (its "natural" normal derived from point order is -Z), while its
    # default thickness offset goes to +Z, so `from_global_outlines` flips the frame. The fix negates the local
    # x-axis on flip instead of swapping x/y, so local x stays aligned with outline_a[0]->outline_a[1] (0, 20, 0),
    # i.e. -world-Y here, and local y ends up along +world-X. The frame origin moves to the matching box corner.
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert plate_a.frame.point == Point(0, 20, 0)
    assert plate_a.frame.xaxis == Vector(0, -1, 0)
    assert plate_a.frame.yaxis == Vector(1, 0, 0)
    assert plate_a.frame.zaxis == Vector(0, 0, 1), "Expected plate frame zaxis to be along global z axis"


def test_plate_frame_flipped_vector():
    # explicit vector=(0, 0, -1) forces the flip branch (outline_b offset opposite the outline's natural normal).
    # Local x stays aligned with outline_a[0]->outline_a[1] = (10, 0, 0), i.e. -world-X after the flip negates it.
    polyline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1, vector=Vector(0, 0, -1))
    assert plate_a.frame.point == Point(10, 0, 0)
    assert plate_a.frame.xaxis == Vector(-1, 0, 0)
    assert plate_a.frame.yaxis == Vector(0, 1, 0)
    assert plate_a.frame.zaxis == Vector(0, 0, -1), "Expected plate frame zaxis to be along global z axis"


def test_plate_blank():
    # this outline triggers the frame flip (see test_plate_frame): local x follows outline_a[0]->outline_a[1]
    # (the 20-long edge, extended to 21 by outline_b), so length/xsize and width/ysize are swapped vs. before the fix.
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(1, 1, 1), Point(1, 21, 1), Point(11, 21, 1), Point(11, 1, 1), Point(1, 1, 1)])
    plate_a = Plate.from_outlines(polyline_a, polyline_b)
    blank = plate_a.blank
    assert plate_a.length == 21, "Expected plate length to be 21"
    assert plate_a.width == 11, "Expected plate width to be 11"
    assert plate_a.thickness == 1, "Expected plate thickness to be 1"
    assert blank.xsize == 21, "Expected blank xsize to be 21"
    assert blank.ysize == 11, "Expected blank ysize to be 11"
    assert blank.zsize == 1, "Expected blank zsize to be 1"
    assert blank.frame.point == Point(5.5, 10.5, 0.5), "Expected blank center to match plate center"


def test_plate_serialization():
    plate = Plate(Frame.worldXY(), 10, 20, 1)
    plate = json_loads(json_dumps(plate))
    assert plate.frame == Frame.worldXY()
    assert plate.length == 10
    assert plate.width == 20
    assert plate.thickness == 1


def test_plate_serialization_with_attributes_kwargs():
    plate = Plate(Frame.worldXY(), 10, 20, 1, custom_attribute="test_value", another_attribute=123)

    plate = json_loads(json_dumps(plate))

    assert plate.frame == Frame.worldXY()
    assert plate.length == 10
    assert plate.width == 20
    assert plate.thickness == 1
    assert plate.attributes["custom_attribute"] == "test_value"
    assert plate.attributes["another_attribute"] == 123


def test_plate_serialization_with_attributes():
    plate = Plate(Frame.worldXY(), 10, 20, 1)
    plate.attributes["custom_attribute"] = "test_value"
    plate.attributes["another_attribute"] = 123

    plate = json_loads(json_dumps(plate))

    assert plate.frame == Frame.worldXY()
    assert plate.length == 10
    assert plate.width == 20
    assert plate.thickness == 1
    assert plate.attributes["custom_attribute"] == "test_value"
    assert plate.attributes["another_attribute"] == 123


def test_sloped_plate_serialization():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate = Plate.from_outline_thickness(polyline_a, 1)

    plate_copy = json_loads(json_dumps(plate))

    assert plate.frame.point == plate_copy.frame.point, "Expected plate frame to match input polyline"
    assert all([TOL.is_allclose(plate.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate.outline_a.points))]), "Expected plate to match input polyline"
    assert all([TOL.is_allclose(plate_copy.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate.outline_a.points))]), "Expected plate to match input polyline"
    assert TOL.is_close(plate.thickness, plate_copy.thickness), "Expected plate thickness to match input thickness"
    assert TOL.is_close(plate.length, plate_copy.length), "Expected plate length to be 10*sqrt(2)"
    assert TOL.is_close(plate.width, plate_copy.width), "Expected plate width to be 20"


def test_from_outline_thickness():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    plate_a = Plate.from_outlines(polyline_a, polyline_b)
    plate_b = Plate.from_outline_thickness(polyline_a, 1)

    for pt_a, pt_b in zip(plate_a.outline_b, plate_b.outline_b):
        assert TOL.is_allclose(pt_a, pt_b)


def test_set_extension_plane():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = Plate.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    plane_copies = [plane.copy() for plane in pg.edge_planes.values()]
    assert all([TOL.is_allclose(planes[i].normal, plane_copies[i].normal) for i in range(0, 3)])
    assert TOL.is_allclose(plane.normal, plane_copies[3].normal)
    assert not TOL.is_allclose(planes[3].normal, plane_copies[3].normal)


def test_apply_and_remove_exensions():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = Plate.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]

    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(polyline_b))])
    pg.remove_blank_extension()
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])
    for i in range(len(planes)):
        assert TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal)


def test_apply_and_remove_exensions_with_index():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = Plate.from_outlines(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(2)  # removing extension at index 2 should not affect index 3
    assert TOL.is_allclose(plane.normal, pg.edge_planes[3].normal)
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(3)  # removing extension at index 3 revert to original
    assert all([TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal) for i in range(len(planes))])
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])


def test_from_face_thickness_rectangular():
    pts = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    brep = make_single_face_brep(pts)
    thickness = 1.0
    plate = Plate.from_face_thickness(brep, thickness)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert plate.outline_a is not None
    assert plate.outline_b is not None
    assert len(plate.outline_a.points) == 5
    assert len(plate.outline_b.points) == 5

    for pt_a, pt_b in zip(plate.outline_a.points, plate.outline_b.points):
        assert TOL.is_close(pt_a.distance_to_point(pt_b), thickness)


def test_from_face_thickness_with_custom_vector():
    pts = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    brep = make_single_face_brep(pts)
    thickness = 1.0
    vector = Vector(0, 0, -1)
    plate = Plate.from_face_thickness(brep, thickness, vector=vector)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert TOL.is_allclose(plate.normal, [0, 0, -1])


def test_from_face_thickness_raises_on_multi_face_brep():
    pts_a = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    pts_b = [Point(0, 0, 1), Point(10, 0, 1), Point(10, 20, 1), Point(0, 20, 1)]
    multi_face_brep = make_plate_brep(pts_a, pts_b)

    with pytest.raises(ValueError):
        Plate.from_face_thickness(multi_face_brep, 1.0)


def test_from_outline_with_openings():
    outline = Polyline([Point(0, 0, 0), Point(20, 0, 0), Point(20, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    opening = Polyline([Point(5, 5, 0), Point(10, 5, 0), Point(10, 10, 0), Point(5, 10, 0), Point(5, 5, 0)])
    thickness = 1.0
    plate = Plate.from_outline_thickness(outline, thickness, openings=[opening])

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert len(plate._features) == 1


def test_from_brep_rectangular_box():
    thickness = 1.0
    pts_a = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    pts_b = [Point(0, 0, thickness), Point(10, 0, thickness), Point(10, 20, thickness), Point(0, 20, thickness)]
    brep = make_plate_brep(pts_a, pts_b)

    plate = Plate.from_brep(brep)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness, atol=0.01)
    assert plate.outline_a is not None
    assert plate.outline_b is not None
    assert len(plate.outline_a.points) == 5
    assert len(plate.outline_b.points) == 5
    assert TOL.is_close(plate.length, 10.0, atol=0.5)
    assert TOL.is_close(plate.width, 20.0, atol=0.5)


def test_from_brep_octagonal_prism():
    import math

    radius = 10.0
    thickness = 2.0
    n_sides = 8

    pts_a = [Point(radius * math.cos(2 * math.pi * i / n_sides), radius * math.sin(2 * math.pi * i / n_sides), 0) for i in range(n_sides)]
    pts_b = [Point(pt.x, pt.y, thickness) for pt in pts_a]
    brep = make_plate_brep(pts_a, pts_b)

    plate = Plate.from_brep(brep)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness, atol=0.1)
    assert len(plate.outline_a.points) == n_sides + 1
    assert len(plate.outline_b.points) == n_sides + 1


def test_from_brep_tilted_box():
    import math

    angle = math.pi / 4
    thickness = 1.0
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    base = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]

    pts_a = [Point(pt.x, pt.y * cos_a, pt.y * sin_a) for pt in base]
    normal_scaled = Vector(0, -sin_a, cos_a) * thickness
    pts_b = [Point(pt.x + normal_scaled.x, pt.y + normal_scaled.y, pt.z + normal_scaled.z) for pt in pts_a]
    brep = make_plate_brep(pts_a, pts_b)

    plate = Plate.from_brep(brep)

    assert plate is not None
    assert plate.outline_a is not None
    assert plate.outline_b is not None
    assert len(plate.outline_a.points) == len(plate.outline_b.points)


def test_from_outlines_mismatched_points_raises():
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 20, 1), Point(0, 0, 1)])

    with pytest.raises((ValueError, AssertionError)):
        Plate.from_outlines(outline_a, outline_b)


def test_from_outlines_validates_closure():
    thickness = 1.0
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, thickness), Point(10, 0, thickness), Point(10, 20, thickness), Point(0, 20, thickness), Point(0, 0, thickness)])

    plate = Plate.from_outlines(outline_a, outline_b)
    assert plate is not None
    assert TOL.is_allclose(plate.outline_a.points[0], plate.outline_a.points[-1])
    assert TOL.is_allclose(plate.outline_b.points[0], plate.outline_b.points[-1])


def test_from_outlines_alignment():
    thickness = 2.0
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 15, 0), Point(0, 15, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, thickness), Point(10, 0, thickness), Point(10, 15, thickness), Point(0, 15, thickness), Point(0, 0, thickness)])
    plate = Plate.from_outlines(outline_a, outline_b)

    assert len(plate.outline_a.points) == len(plate.outline_b.points)

    distances = []
    for pt_a, pt_b in zip(plate.outline_a.points[:-1], plate.outline_b.points[:-1]):
        dist = pt_a.distance_to_point(pt_b)
        distances.append(dist)

    avg_distance = sum(distances) / len(distances)
    for dist in distances:
        assert TOL.is_close(dist, avg_distance, atol=0.1)
    assert TOL.is_close(avg_distance, thickness, atol=0.1)


# ---------------------------------------------------------------------------
# orientation parameter
# ---------------------------------------------------------------------------

_FLAT_OUTLINE = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
_SLOPED_OUTLINE = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])


def test_plate_orientation_does_not_change_normal_or_outlines():
    plate_default = Plate.from_outline_thickness(_FLAT_OUTLINE, 1)
    plate_oriented = Plate.from_outline_thickness(_FLAT_OUTLINE, 1, orientation=Vector(0, 1, 0))

    assert TOL.is_allclose(plate_default.normal, plate_oriented.normal)
    assert TOL.is_close(plate_default.thickness, plate_oriented.thickness)
    for pt_d, pt_o in zip(plate_default.outline_a.points, plate_oriented.outline_a.points):
        assert TOL.is_allclose(pt_d, pt_o)
    for pt_d, pt_o in zip(plate_default.outline_b.points, plate_oriented.outline_b.points):
        assert TOL.is_allclose(pt_d, pt_o)


def test_plate_orientation_changes_local_frame():
    plate_default = Plate.from_outline_thickness(_FLAT_OUTLINE, 1)
    plate_oriented = Plate.from_outline_thickness(_FLAT_OUTLINE, 1, orientation=Vector(0, 1, 0))

    assert not TOL.is_allclose(plate_default.frame.xaxis, plate_oriented.frame.xaxis)
    assert not TOL.is_allclose(plate_default.frame.yaxis, plate_oriented.frame.yaxis)


def test_plate_orientation_explicit_frame_flat():
    # orientation=Y on this flat plate forces the plate's local yaxis to align with the world Y axis, and the xaxis to be perpendicular to it
    plate = Plate.from_outline_thickness(_FLAT_OUTLINE, 1, orientation=Vector(0, 1, 0))
    assert TOL.is_allclose(plate.frame.xaxis, [1, 0, 0])
    assert TOL.is_allclose(plate.frame.yaxis, [0, 1, 0])


def test_plate_orientation_explicit_frame_sloped():
    # orientation=X on the sloped plate: yaxis aligns with the plate's slope direction
    plate = Plate.from_outline_thickness(_SLOPED_OUTLINE, 1, orientation=Vector(1, 0, 0))
    assert TOL.is_allclose(plate.frame.xaxis, [0, 0.7071067811865476, 0.7071067811865476])
    assert TOL.is_allclose(plate.frame.yaxis, [1, 0, 0])


def test_plate_from_outlines_orientation():
    outline_b = Polyline([Point(pt[0], pt[1], pt[2] + 1) for pt in _FLAT_OUTLINE.points])
    plate_default = Plate.from_outlines(_FLAT_OUTLINE, outline_b)
    plate_oriented = Plate.from_outlines(_FLAT_OUTLINE, outline_b, orientation=Vector(0, 1, 0))

    assert not TOL.is_allclose(plate_default.frame.xaxis, plate_oriented.frame.xaxis)
    assert TOL.is_allclose(plate_default.normal, plate_oriented.normal)
