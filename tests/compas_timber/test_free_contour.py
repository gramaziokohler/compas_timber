import pytest

from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL
from compas_timber.fabrication import BTLxWriter

from compas_timber.elements import Plate
from compas_timber.fabrication import FreeContour
from compas.data import json_loads
from compas.data import json_dumps


@pytest.fixture
def plate():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    return Plate(pline, 10.0)


def test_plate_blank():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    plate = Plate(pline, 10.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 200.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 100.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_reversed():
    pline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 200, 0), Point(0, 200, 0), Point(0, 0, 0)])
    plate = Plate(pline, 10.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 100.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 200.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_extension():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    plate = Plate(pline, 10.0, blank_extension=5.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 210.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 110.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_contour():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    plate = Plate(pline, thickness)

    expected = {
        "header_attributes": {"ToolID": "0", "Name": "FreeContour", "ToolPosition": "right", "ReferencePlaneID": "4", "CounterSink": "no", "Process": "yes"},
        "contour_attributes": {"Inclination": "0", "DepthBounded": "no", "Depth": "10.0"},
        "contour_points": [
            {"StartPoint": {"Y": "105.000", "X": "5.000", "Z": "0.000"}},
            {"Line": {"EndPoint": {"Y": "105.000", "X": "205.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "5.000", "X": "205.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "5.000", "X": "5.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "105.000", "X": "5.000", "Z": "0.000"}}},
        ],
    }

    assert plate.features[0].header_attributes == expected["header_attributes"]
    assert plate.features[0].contour_attributes["Depth"] == str(thickness)


def test_plate_aperture_contour():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth)
    plate.add_feature(contour)

    assert len(plate.features) == 2
    assert plate.features[1] == contour
    assert contour.header_attributes["ToolPosition"] == "left"
    assert contour.header_attributes["CounterSink"] == "yes"
    assert contour.contour_attributes["Depth"] == str(depth)


def test_plate_aperture_contour_serialization():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth)

    contour_copy = json_loads(json_dumps(contour))
    plate.add_feature(contour_copy)

    assert len(plate.features) == 2
    assert plate.features[1] == contour_copy
    assert contour_copy.header_attributes["ToolPosition"] == "left"
    assert contour_copy.header_attributes["CounterSink"] == "yes"
    assert contour_copy.contour_attributes["Depth"] == str(depth)


def test_plate_aperture_BTLx():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth)

    contour_copy = json_loads(json_dumps(contour))
    plate.add_feature(contour_copy)

    processing_element = BTLxWriter._create_processing_from_dict(contour.processing_dict())

    assert processing_element.tag == "FreeContour"
    assert processing_element.attrib == contour.header_attributes
