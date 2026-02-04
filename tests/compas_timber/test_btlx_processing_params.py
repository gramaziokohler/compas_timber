from unittest.mock import MagicMock
from collections import OrderedDict

from compas_timber.fabrication.btlx import BTLxProcessing
from compas_timber.fabrication.btlx import BTLxProcessingParams
from compas_timber.fabrication.btlx import MachiningLimits


class _TestProcessingParams(BTLxProcessingParams):
    """Minimal concrete implementation for testing BTLxProcessingParams."""

    def __init__(self, instance, attr_map):
        super(_TestProcessingParams, self).__init__(instance)
        self._attr_map = attr_map

    @property
    def attribute_map(self):
        return self._attr_map


class TestBTLxProcessingParams:
    """Tests for BTLxProcessingParams class."""

    def test_as_dict_uses_attribute_map(self):
        """Test that as_dict() uses attribute_map to build the result dictionary."""
        # Create a mock processing instance with test attributes
        mock_processing = MagicMock(spec=BTLxProcessing)
        mock_processing.test_str = "hello"
        mock_processing.test_int = 100
        mock_processing.test_float = 1.5
        mock_processing.test_bool = False
        mock_processing.test_machining_limits = MachiningLimits()

        # Create attribute map
        attr_map = {
            "TestString": "test_str",
            "TestInteger": "test_int",
            "TestFloat": "test_float",
            "TestBoolean": "test_bool",
            "MachiningLimits": "test_machining_limits",
        }

        # Create a real params instance with the mock processing
        params = _TestProcessingParams(mock_processing, attr_map)

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
        mock_processing = MagicMock(spec=BTLxProcessing)
        mock_processing.test_str = "world"
        mock_processing.test_int = 42
        mock_processing.test_float = 3.14159
        mock_processing.test_bool = True
        mock_processing.test_machining_limits = machining_limits

        # Create attribute map
        attr_map = {
            "TestString": "test_str",
            "TestInteger": "test_int",
            "TestFloat": "test_float",
            "TestBoolean": "test_bool",
            "MachiningLimits": "test_machining_limits",
        }

        # Create a real params instance with the mock processing
        params = _TestProcessingParams(mock_processing, attr_map)

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
