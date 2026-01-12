from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Frame
from compas.data import json_dumps
from compas.data import json_loads
from compas.tolerance import TOL

from compas_timber.elements import Plate
from compas_timber.elements import PlateGeometry


def test_flat_plate_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert plate_a.thickness == 1, "Expected plate thickness to match input thickness"
    assert plate_a.length == 10, "Expected plate length to be 10"
    assert plate_a.width == 20, "Expected plate width to be 20"


def test_sloped_plate_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    assert plate_a.frame.point == Point(0, 10, 0), "Expected plate frame to match input polyline"
    assert all([TOL.is_allclose(plate_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(plate_a.outline_a.points))]), "Expected plate to match input polyline"
    assert TOL.is_close(plate_a.thickness, 1), "Expected plate thickness to match input thickness"
    assert TOL.is_close(plate_a.length, 14.1421356237), "Expected plate length to be 10*sqrt(2)"
    assert TOL.is_close(plate_a.width, 20), "Expected plate width to be 20"


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

