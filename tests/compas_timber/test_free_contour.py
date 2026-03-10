import pytest
import math

from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL
from compas_timber.fabrication import BTLxWriter

from compas_timber.elements import Plate
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import Contour
from compas_timber.fabrication import DualContour
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
    assert TOL.is_zero(plate.blank.xsize - 100.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 200.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_reversed():
    pline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 200, 0), Point(0, 200, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(pline, 10.0)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 200.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 100.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_blank_extension():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(pline, 10.0)
    plate.attributes["blank_extension"] = 5.0

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 110.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 210.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_plate_contour():
    pline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    thickness = 10.0
    plate = Plate.from_outline_thickness(pline, thickness)

    expected = {
        "header_attributes": {
            "Priority": "0",
            "ProcessID": "0",
            "ToolID": "0",
            "Name": "FreeContour",
            "ToolPosition": "right",
            "ReferencePlaneID": "1",
            "CounterSink": "no",
            "Process": "yes",
        },
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
    contour = FreeContour.from_polyline_and_element(aperture_pline, plate, depth=depth, interior=True)
    plate.add_features(contour)

    assert len(plate.features) == 2
    assert plate.features[1] == contour
    assert contour.params.header_attributes["ToolPosition"] == "left"
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
    plate.add_features(contour_copy)

    assert len(plate.features) == 2
    assert plate.features[1] == contour_copy
    assert contour_copy.params.header_attributes["ToolPosition"] == "left"
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
    plate.add_features(contour_copy)

    processing_element = BTLxWriter()._create_processing(contour)

    assert processing_element.tag == "FreeContour"
    assert processing_element.attrib == contour.params.header_attributes


def test_double_contour_plate():
    pline_a = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    pline_b = Polyline([Point(-10, -10, 10), Point(-10, 210, 10), Point(110, 210, 10), Point(110, -10, 10), Point(-10, -10, 10)])
    plate = Plate.from_outlines(pline_a, pline_b)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 120.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 220.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_contour_plate_blank():
    pline_a = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    pline_b = Polyline([Point(-10, -10, 10), Point(-10, 210, 10), Point(110, 210, 10), Point(110, -10, 10), Point(-10, -10, 10)])
    plate = Plate.from_outlines(pline_a, pline_b)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 120.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 220.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)


def test_contour_plate_simple_inclination():
    pline_a = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    pline_b = Polyline([Point(-10, -10, 10), Point(-10, 210, 10), Point(110, 210, 10), Point(110, -10, 10), Point(-10, -10, 10)])
    plate = Plate.from_outlines(pline_a, pline_b)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert TOL.is_zero(plate.blank.xsize - 120.0)  # x-axis is the vector from `plate.outline[0]` to `plate.outline[1]`
    assert TOL.is_zero(plate.blank.ysize - 220.0)
    assert TOL.is_zero(plate.blank.zsize - 10.0)
    assert TOL.is_close(plate.features[0].params.as_dict()["Contour"].inclination[0], -45.0)


def test_contour_plate_multiple_inclination():
    pline_a = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    pline_b = Polyline(
        [
            Point(-10, -10 * math.tan(math.pi / 6), 10),
            Point(-10, 210, 10),
            Point(110, 210, 10),
            Point(110, -10 * math.tan(math.pi / 6), 10),
            Point(-10, -10 * math.tan(math.pi / 6), 10),
        ]
    )
    plate = Plate.from_outlines(pline_a, pline_b)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert isinstance(plate.features[0].params.as_dict().get("Contour"), Contour)
    assert TOL.is_allclose(plate.features[0].params.as_dict()["Contour"].inclination, [-45.0, -45.0, -45.0, -30.0])


def test_dual_contour_plate():
    pline_a = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    pline_b = Polyline(
        [
            Point(10, 10 * math.tan(math.pi / 6), 10),
            Point(-10, 210, 10),
            Point(110, 210, 10),
            Point(110, -10 * math.tan(math.pi / 6), 10),
            Point(10, 10 * math.tan(math.pi / 6), 10),
        ]
    )
    plate = Plate.from_outlines(pline_a, pline_b)

    assert len(plate.features) == 1
    assert isinstance(plate.features[0], FreeContour)
    assert isinstance(plate.features[0].params.as_dict().get("Contour"), DualContour)


def test_contour_scaled():
    polyline = Polyline([Point(0, 0, 0), Point(0, 200, 0), Point(100, 200, 0), Point(100, 0, 0), Point(0, 0, 0)])
    depth = 10.0
    contour = Contour(polyline=polyline, depth=depth)

    scaled_contour = contour.scaled(2.0)

    assert TOL.is_allclose(scaled_contour.polyline, contour.polyline.scaled(2.0))
    assert scaled_contour.depth == contour.depth * 2.0
    assert scaled_contour.inclination == contour.inclination
    assert scaled_contour.depth_bounded == contour.depth_bounded
