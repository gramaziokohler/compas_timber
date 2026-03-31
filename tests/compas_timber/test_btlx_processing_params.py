from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.elements import Plate
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import Contour
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import Mortise
from compas_timber.fabrication.btlx import AttributeSpec
from compas_timber.fabrication.btlx import BTLxProcessingParams


class _MockProcessing(BTLxProcessing):
    """Mock processing class with ATTRIBUTE_MAP for testing."""

    PROCESSING_NAME = "MockProcessing"
    ATTRIBUTE_MAP = {
        "TestString": AttributeSpec("test_str"),
        "TestInteger": AttributeSpec("test_int"),
        "TestFloat": AttributeSpec("test_float"),
        "TestBoolean": AttributeSpec("test_bool"),
        "MachiningLimits": AttributeSpec("test_machining_limits"),
    }

    def __init__(self, test_str="", test_int=0, test_float=0.0, test_bool=False, test_machining_limits=None):
        super(_MockProcessing, self).__init__()
        self._test_str = test_str
        self._test_int = test_int
        self._test_float = test_float
        self._test_bool = test_bool
        self._test_machining_limits = test_machining_limits or MachiningLimits()

    @property
    def test_str(self):
        return self._test_str

    @property
    def test_int(self):
        return self._test_int

    @property
    def test_float(self):
        return self._test_float

    @property
    def test_bool(self):
        return self._test_bool

    @property
    def test_machining_limits(self):
        return self._test_machining_limits

    @property
    def __data__(self):
        data = super(_MockProcessing, self).__data__
        data["test_str"] = self.test_str
        data["test_int"] = self.test_int
        data["test_float"] = self.test_float
        data["test_bool"] = self.test_bool
        return data


# --- as_dict() ---


def test_as_dict_returns_ordered_dict():
    processing = _MockProcessing(test_str="hello", test_int=100, test_float=1.5, test_bool=False)
    result = processing.params.as_dict()
    assert isinstance(result, OrderedDict)


def test_as_dict_keys_come_from_attribute_map():
    processing = _MockProcessing()
    result = processing.params.as_dict()
    for key in _MockProcessing.ATTRIBUTE_MAP:
        assert key in result


def test_as_dict_formats_string():
    processing = _MockProcessing(test_str="hello")
    assert processing.params.as_dict()["TestString"] == "hello"


def test_as_dict_formats_int():
    processing = _MockProcessing(test_int=100)
    assert processing.params.as_dict()["TestInteger"] == "100.000"


def test_as_dict_formats_float():
    processing = _MockProcessing(test_float=1.5)
    assert processing.params.as_dict()["TestFloat"] == "1.500"


def test_as_dict_formats_bool_false():
    processing = _MockProcessing(test_bool=False)
    assert processing.params.as_dict()["TestBoolean"] == "no"


def test_as_dict_formats_bool_true():
    processing = _MockProcessing(test_bool=True)
    assert processing.params.as_dict()["TestBoolean"] == "yes"


def test_as_dict_formats_machining_limits():
    limits = MachiningLimits(face_limited_start=True, face_limited_end=False)
    processing = _MockProcessing(test_machining_limits=limits)
    result = processing.params.as_dict()["MachiningLimits"]
    assert isinstance(result, dict)
    assert result["FaceLimitedStart"] == "yes"
    assert result["FaceLimitedEnd"] == "no"


# --- _format_value() ---


def test_format_value_bool_true():
    assert BTLxProcessingParams._format_value(True) == "yes"


def test_format_value_bool_false():
    assert BTLxProcessingParams._format_value(False) == "no"


def test_format_value_int():
    assert BTLxProcessingParams._format_value(42) == "42.000"
    assert BTLxProcessingParams._format_value(0) == "0.000"
    assert BTLxProcessingParams._format_value(-10) == "-10.000"


def test_format_value_float():
    assert BTLxProcessingParams._format_value(3.14159) == "3.142"
    assert BTLxProcessingParams._format_value(0.0) == "0.000"
    assert BTLxProcessingParams._format_value(-2.5) == "-2.500"


def test_format_value_string():
    assert BTLxProcessingParams._format_value("test") == "test"
    assert BTLxProcessingParams._format_value("") == ""
    assert BTLxProcessingParams._format_value("start") == "start"


def test_format_value_machining_limits():
    limits = MachiningLimits(
        face_limited_start=True,
        face_limited_end=False,
        face_limited_front=True,
        face_limited_back=False,
        face_limited_top=True,
        face_limited_bottom=False,
    )
    result = BTLxProcessingParams._format_value(limits)
    assert isinstance(result, dict)
    assert result["FaceLimitedStart"] == "yes"
    assert result["FaceLimitedEnd"] == "no"
    assert result["FaceLimitedFront"] == "yes"
    assert result["FaceLimitedBack"] == "no"
    assert result["FaceLimitedTop"] == "yes"
    assert result["FaceLimitedBottom"] == "no"


def test_format_value_contour_passthrough():
    polyline = [Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 100, 0), Point(0, 0, 0)]
    contour = Contour(polyline, depth=10.0, depth_bounded=True, inclination=[90.0])
    assert "Contour" in BTLxWriter.SERIALIZERS
    result = BTLxProcessingParams._format_value(contour)
    assert result is contour


# --- Integration with real processings ---


def test_mortise_params_returns_btlx_processing_params_instance():
    mortise = Mortise(
        start_x=10.0,
        start_y=20.0,
        start_depth=5.0,
        angle=90.0,
        slope=90.0,
        inclination=90.0,
        length_limited_top=True,
        length_limited_bottom=False,
        length=100.0,
        width=50.0,
        depth=30.0,
        shape="automatic",
        shape_radius=0.0,
    )
    assert isinstance(mortise.params, BTLxProcessingParams)


def test_mortise_params_as_dict_keys():
    mortise = Mortise(
        start_x=10.0,
        start_y=20.0,
        start_depth=5.0,
        angle=90.0,
        slope=90.0,
        inclination=90.0,
        length_limited_top=True,
        length_limited_bottom=False,
        length=100.0,
        width=50.0,
        depth=30.0,
        shape="automatic",
        shape_radius=0.0,
    )
    result = mortise.params.as_dict()
    assert isinstance(result, OrderedDict)
    for key in ("StartX", "StartY", "Angle", "Length", "Width", "Depth"):
        assert key in result


def test_mortise_params_as_dict_values():
    mortise = Mortise(
        start_x=10.0,
        start_y=20.0,
        start_depth=5.0,
        angle=90.0,
        slope=90.0,
        inclination=90.0,
        length_limited_top=True,
        length_limited_bottom=False,
        length=100.0,
        width=50.0,
        depth=30.0,
        shape="automatic",
        shape_radius=0.0,
    )
    result = mortise.params.as_dict()
    assert result["StartX"] == "10.000"
    assert result["StartY"] == "20.000"
    assert result["Angle"] == "90.000"
    assert result["Length"] == "100.000"
    assert result["Width"] == "50.000"
    assert result["Depth"] == "30.000"


def test_free_contour_params_contour_passthrough():
    plate_polyline = Polyline([Point(0, 0, 0), Point(200, 0, 0), Point(200, 100, 0), Point(0, 100, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(plate_polyline, 10.0)
    contour_polyline = Polyline([Point(10, 10, 0), Point(190, 10, 0), Point(190, 90, 0), Point(10, 90, 0), Point(10, 10, 0)])
    free_contour = FreeContour.from_polyline_and_element(contour_polyline, plate, depth=5.0)
    result = free_contour.params.as_dict()
    assert "Contour" in result
    assert isinstance(result["Contour"], Contour)
    assert result["Contour"].depth == 5.0
