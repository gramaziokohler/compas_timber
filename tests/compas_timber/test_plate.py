import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Frame
from compas.geometry import Box
from compas.geometry import Plane

from compas.tolerance import TOL

from compas_timber.elements import Plate


def test_flat_plate_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [([0, 0, 0], [-1, 0, 0]), ([0, 20, 0], [0, 1, 0]), ([10, 20, 0], [1, 0, 0]), ([10, 0, 0], [0, -1, 0])]
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert plate_a.thickness == 1, "Expected plate thickness to match input thickness"
    assert plate_a.length == 10, "Expected plate length to be 10"
    assert plate_a.width == 20, "Expected plate width to be 20"
    assert TOL.is_allclose(plate_a.normal, [0, 0, 1]), "Expected the normal to be the world Z-axis"
    for expected, plane in zip(expected_edge_planes, plate_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    for obb_pt, expected_pt in zip(plate_a.obb.points, Box.from_points([Point(0, 0, 0), Point(10, 20, 1)]).points):
        assert TOL.is_allclose(obb_pt, expected_pt)


def test_sloped_plate_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [
        ([0, 10, 0], [0, -0.707106781, -0.707106781]),
        ([10, 10, 0], [0.81649658, -0.40824829, -0.40824829]),
        ([20, 20, 10], [0, 0.707106781, 0.707106781]),
        ([0, 20, 10], [-1, 0, 0]),
    ]

    expected_obb = Box(
        xsize=14.142135623730951,
        ysize=20.0,
        zsize=1.0,
        frame=Frame(
            point=Point(x=10.0, y=15.353553390593273, z=4.646446609406729), xaxis=Vector(x=0.0, y=0.7071067811865475, z=0.7071067811865476), yaxis=Vector(x=1.0, y=0.0, z=0.0)
        ),
    )

    assert plate_a.frame.point == Point(0, 10, 0), "Expected plate frame to match input polyline"
    assert all([TOL.is_allclose(plate_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert TOL.is_close(plate_a.thickness, 1), "Expected plate thickness to match input thickness"
    assert TOL.is_close(plate_a.length, 14.1421356237), "Expected plate length to be 10*sqrt(2)"
    assert TOL.is_close(plate_a.width, 20), "Expected plate width to be 20"
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
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert plate_a.frame.point == Point(0, 0, 0), "Expected plate frame point to be at origin"
    assert plate_a.frame.xaxis == Vector(1, 0, 0), "Expected plate frame xaxis to be along global x axis"
    assert plate_a.frame.yaxis == Vector(0, 1, 0), "Expected plate frame yaxis to be along global y axis"
    assert plate_a.frame.zaxis == Vector(0, 0, 1), "Expected plate frame zaxis to be along global z axis"


def test_plate_frame_flipped_vector():
    polyline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1, vector=Vector(0, 0, -1))
    assert plate_a.frame.point == Point(0, 0, 0), "Expected plate frame point to be at origin"
    assert plate_a.frame.xaxis == Vector(0, 1, 0), "Expected plate frame xaxis to be along global y axis"
    assert plate_a.frame.yaxis == Vector(1, 0, 0), "Expected plate frame yaxis to be along negative global x axis"
    assert plate_a.frame.zaxis == Vector(0, 0, -1), "Expected plate frame zaxis to be along global z axis"


def test_plate_blank():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(1, 1, 1), Point(1, 21, 1), Point(11, 21, 1), Point(11, 1, 1), Point(1, 1, 1)])
    plate_a = Plate.from_outlines(polyline_a, polyline_b)
    blank = plate_a.blank
    assert plate_a.length == 11, "Expected plate length to be 11"
    assert plate_a.width == 21, "Expected plate width to be 21"
    assert plate_a.thickness == 1, "Expected plate thickness to be 1"
    assert blank.xsize == 11, "Expected blank xsize to be 11"
    assert blank.ysize == 21, "Expected blank ysize to be 21"
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


def test_from_face_rectangular():
    outline = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    thickness = 1.0
    plate = Plate.from_outline_thickness(outline, thickness)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert plate.outline_a is not None
    assert plate.outline_b is not None
    assert len(plate.outline_a.points) == 5
    assert len(plate.outline_b.points) == 5

    for pt_a, pt_b in zip(plate.outline_a.points, plate.outline_b.points):
        assert TOL.is_close(pt_a.distance_to_point(pt_b), thickness)


def test_from_face_with_custom_vector():
    outline = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    thickness = 1.0
    vector = Vector(0, 0, -1)
    plate = Plate.from_outline_thickness(outline, thickness, vector=vector)

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert TOL.is_allclose(plate.normal, [0, 0, -1])


def test_from_outline_with_openings():
    outline = Polyline([Point(0, 0, 0), Point(20, 0, 0), Point(20, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    opening = Polyline([Point(5, 5, 0), Point(10, 5, 0), Point(10, 10, 0), Point(5, 10, 0), Point(5, 5, 0)])
    thickness = 1.0
    plate = Plate.from_outline_thickness(outline, thickness, openings=[opening])

    assert plate is not None
    assert TOL.is_close(plate.thickness, thickness)
    assert len(plate.plate_geometry.openings) == 1


def test_from_brep_rectangular_box():
    thickness = 1.0
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, thickness), Point(10, 0, thickness), Point(10, 20, thickness), Point(0, 20, thickness), Point(0, 0, thickness)])
    plate = Plate.from_outlines(outline_a, outline_b)

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

    points_bottom = []
    for i in range(n_sides):
        angle = 2 * math.pi * i / n_sides
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points_bottom.append(Point(x, y, 0))
    points_bottom.append(points_bottom[0])

    points_top = []
    for pt in points_bottom:
        points_top.append(Point(pt.x, pt.y, thickness))

    polyline_bottom = Polyline(points_bottom)
    polyline_top = Polyline(points_top)
    plate = Plate.from_outlines(polyline_bottom, polyline_top)

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
    base_points = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0), Point(0, 0, 0)]

    points_bottom = []
    for pt in base_points:
        new_x = pt.x
        new_y = pt.y * cos_a
        new_z = pt.y * sin_a
        points_bottom.append(Point(new_x, new_y, new_z))
    outline_bottom = Polyline(points_bottom)

    normal = Vector(0, -sin_a, cos_a)
    normal_scaled = normal * thickness

    points_top = []
    for pt in points_bottom:
        points_top.append(Point(pt.x + normal_scaled.x, pt.y + normal_scaled.y, pt.z + normal_scaled.z))
    outline_top = Polyline(points_top)

    plate = Plate.from_outlines(outline_bottom, outline_top)

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
