from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Polyline
from compas_timber.elements import Plate
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Contour
from compas_timber.fabrication.btlx import BTLxProcessingParams


class _MockProcessing(BTLxProcessing):
    """Mock processing class with ATTRIBUTE_MAP for testing."""

    PROCESSING_NAME = "MockProcessing"
    ATTRIBUTE_MAP = {
        "TestString": "test_str",
        "TestInteger": "test_int",
        "TestFloat": "test_float",
        "TestBoolean": "test_bool",
        "MachiningLimits": "test_machining_limits",
    }

    def __init__(self, test_str="", test_int=0, test_float=0.0, test_bool=False, test_machining_limits=None):
        super(_MockProcessing, self).__init__()
        self.test_str = test_str
        self.test_int = test_int
        self.test_float = test_float
        self.test_bool = test_bool
        self.test_machining_limits = test_machining_limits or MachiningLimits()

    @property
    def __data__(self):
        data = super(_MockProcessing, self).__data__
        data["test_str"] = self.test_str
        data["test_int"] = self.test_int
        data["test_float"] = self.test_float
        data["test_bool"] = self.test_bool
        return data


class TestBTLxProcessingParams:
    """Tests for BTLxProcessingParams class."""

    def test_as_dict_uses_attribute_map(self):
        """Test that as_dict() uses processing's ATTRIBUTE_MAP to build the result dictionary."""
        # Create a mock processing instance with test attributes
        processing = _MockProcessing(test_str="hello", test_int=100, test_float=1.5, test_bool=False, test_machining_limits=MachiningLimits())

        # Get params from the processing (uses universal params property)
        params = processing.params

        # Call as_dict() as an instance method
        result = params.as_dict()

        assert isinstance(result, OrderedDict)
        assert "TestString" in result
        assert "TestInteger" in result
        assert "TestFloat" in result
        assert "TestBoolean" in result
        assert "MachiningLimits" in result

        assert result["TestString"] == "hello"
        assert result["TestInteger"] == "100.000"
        assert result["TestFloat"] == "1.500"
        assert result["TestBoolean"] == "no"
        assert isinstance(result["MachiningLimits"], dict)

    def test_as_dict_formats_all_values(self):
        """Test that as_dict() properly formats all attribute values."""
        machining_limits = MachiningLimits(face_limited_start=True, face_limited_end=False)

        # Create a mock processing instance with test attributes
        processing = _MockProcessing(test_str="world", test_int=42, test_float=3.14159, test_bool=True, test_machining_limits=machining_limits)

        # Get params from the processing
        params = processing.params

        # Call as_dict() as an instance method
        result = params.as_dict()

        # Check that all values are formatted correctly
        assert result["TestString"] == "world"
        assert result["TestInteger"] == "42.000"
        assert result["TestFloat"] == "3.142"
        assert result["TestBoolean"] == "yes"

        # Check MachiningLimits conversion
        limits_result = result["MachiningLimits"]
        assert limits_result["FaceLimitedStart"] == "yes"
        assert limits_result["FaceLimitedEnd"] == "no"


class TestFormatValue:
    """Tests for BTLxProcessingParams._format_value() static method."""

    def test_format_bool(self):
        """Test that _format_value correctly formats boolean values."""
        assert BTLxProcessingParams._format_value(True) == "yes"
        assert BTLxProcessingParams._format_value(False) == "no"

    def test_format_int(self):
        """Test that _format_value correctly formats integer values."""
        assert BTLxProcessingParams._format_value(42) == "42.000"
        assert BTLxProcessingParams._format_value(0) == "0.000"
        assert BTLxProcessingParams._format_value(-10) == "-10.000"

    def test_format_float(self):
        """Test that _format_value correctly formats float values."""
        assert BTLxProcessingParams._format_value(3.14159) == "3.142"
        assert BTLxProcessingParams._format_value(0.0) == "0.000"
        assert BTLxProcessingParams._format_value(-2.5) == "-2.500"

    def test_format_string(self):
        """Test that _format_value correctly handles string values."""
        assert BTLxProcessingParams._format_value("test") == "test"
        assert BTLxProcessingParams._format_value("") == ""
        assert BTLxProcessingParams._format_value("start") == "start"

    def test_format_machining_limits(self):
        """Test that _format_value correctly formats MachiningLimits objects."""
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

    def test_format_contour_object(self):
        """Test that _format_value passes through Contour objects unchanged for complex serialization."""
        # Create a Contour object
        polyline = [Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 100, 0), Point(0, 0, 0)]
        contour = Contour(polyline, depth=10.0, depth_bounded=True, inclination=[90.0])

        # Ensure Contour is registered in SERIALIZERS
        assert "Contour" in BTLxWriter.SERIALIZERS

        # _format_value should return the contour unchanged
        result = BTLxProcessingParams._format_value(contour)

        assert result is contour  # Should be the exact same object, not a copy
        assert isinstance(result, Contour)


class TestIntegrationWithRealProcessing:
    """Integration tests using real processing classes."""

    def test_mortise_params_integration(self):
        """Test that Mortise processing uses universal params correctly."""

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

        # Get params using universal property
        params = mortise.params

        # Verify it's a BTLxProcessingParams instance
        assert isinstance(params, BTLxProcessingParams)

        # Call as_dict() and verify it uses Mortise.ATTRIBUTE_MAP
        result = params.as_dict()

        assert isinstance(result, OrderedDict)
        # Check that BTLx parameter names from ATTRIBUTE_MAP are used
        assert "StartX" in result
        assert "StartY" in result
        assert "Angle" in result
        assert "Length" in result
        assert "Width" in result
        assert "Depth" in result

        # Verify values are correctly formatted
        assert result["StartX"] == "10.000"
        assert result["StartY"] == "20.000"
        assert result["Angle"] == "90.000"
        assert result["Length"] == "100.000"
        assert result["Width"] == "50.000"
        assert result["Depth"] == "30.000"

    def test_free_contour_with_contour_parameter(self):
        """Test that FreeContour with Contour parameter serializes correctly."""

        # Create a plate
        plate_polyline = Polyline([Point(0, 0, 0), Point(200, 0, 0), Point(200, 100, 0), Point(0, 100, 0), Point(0, 0, 0)])
        plate = Plate.from_outline_thickness(plate_polyline, 10.0)

        # Create a FreeContour
        contour_polyline = Polyline([Point(10, 10, 0), Point(190, 10, 0), Point(190, 90, 0), Point(10, 90, 0), Point(10, 10, 0)])
        free_contour = FreeContour.from_polyline_and_element(contour_polyline, plate, depth=5.0)

        # Get params
        params = free_contour.params
        result = params.as_dict()

        # The Contour parameter should be passed through unchanged
        assert "Contour" in result
        assert isinstance(result["Contour"], Contour)
        assert result["Contour"].depth == 5.0
