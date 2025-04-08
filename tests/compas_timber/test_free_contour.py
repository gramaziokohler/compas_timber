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
    return Plate.from_outline_thickness(pline, 10.0)


def test_plate_blank():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(pline, 10.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 200.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 100.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_reversed():
    pline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 200, 0), Point(0, 200, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(pline, 10.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 100.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 200.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_extension():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(pline, 10.0, blank_extension=5.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 210.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 110.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_contour():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    plate = Plate.from_outline_thickness(pline, thickness)

    expected = {
        "header_attributes": {"ToolID": "0", "Name": "FreeContour", "ToolPosition": "left", "ReferencePlaneID": "2", "CounterSink": "no", "Process": "yes"},
        "contour_attributes": {"Inclination": "0", "DepthBounded": "no", "Depth": "10.0"},
        "contour_points": [
            {"StartPoint": {"Y": "105.000", "X": "5.000", "Z": "0.000"}},
            {"Line": {"EndPoint": {"Y": "105.000", "X": "205.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "5.000", "X": "205.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "5.000", "X": "5.000", "Z": "0.000"}}},
            {"Line": {"EndPoint": {"Y": "105.000", "X": "5.000", "Z": "0.000"}}},
        ],
    }

    assert plate.features[0].params.header_attributes == expected["header_attributes"]
    assert TOL.is_close(plate.features[0].params.as_dict()["Contour"].depth, thickness)


def test_plate_aperture_contour():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate.from_outline_thickness(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth, interior =True)
    plate.add_feature(contour)

    assert len(plate.features) == 2
    assert plate.features[1] == contour
    assert contour.params.header_attributes["ToolPosition"] == "right"
    assert contour.params.header_attributes["CounterSink"] == "yes"
    assert contour.params.as_dict()["Contour"].depth == depth


def test_plate_aperture_contour_serialization():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate.from_outline_thickness(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth, interior=True)

    contour_copy = json_loads(json_dumps(contour))
    plate.add_feature(contour_copy)

    assert len(plate.features) == 2
    assert plate.features[1] == contour_copy
    assert contour_copy.params.header_attributes["ToolPosition"] == "right"
    assert contour_copy.params.header_attributes["CounterSink"] == "yes"
    assert contour_copy.params.as_dict()["Contour"].depth == depth


def test_plate_aperture_BTLx():
    plate_pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    depth = 5.0
    plate = Plate.from_outline_thickness(plate_pline, thickness)
    aperture_pline = Polyline([Point(25, 50, 0), Point(25, 150, 0), Point(75, 150, 0), Point(75, 50, 0), Point(25, 50, 0)])
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth)

    contour_copy = json_loads(json_dumps(contour))
    plate.add_feature(contour_copy)

    processing_element = BTLxWriter()._create_processing(contour)

    assert processing_element.tag == "FreeContour"
    assert processing_element.attrib == contour.params.header_attributes
