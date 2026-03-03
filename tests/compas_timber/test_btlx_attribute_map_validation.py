import pytest

from compas_timber.fabrication import BTLxProcessing


class _ValidProcessing(BTLxProcessing):
    """Processing with a fully valid ATTRIBUTE_MAP, used as a base for inheritance tests."""

    PROCESSING_NAME = "ValidProcessing"
    ATTRIBUTE_MAP = {
        "StartX": "start_x",
        "StartY": "start_y",
    }

    def __init__(self):
        super(_ValidProcessing, self).__init__()
        self._start_x = 0.0
        self._start_y = 0.0

    @property
    def start_x(self):
        return self._start_x

    @property
    def start_y(self):
        return self._start_y


def test_abc_prevents_instantiation_without_processing_name():
    """ABC should prevent instantiation if PROCESSING_NAME is not implemented."""

    class MissingProcessingName(BTLxProcessing):
        ATTRIBUTE_MAP = {}

    with pytest.raises(TypeError, match=r"Can't instantiate abstract class MissingProcessingName.*abstract method.*PROCESSING_NAME"):
        MissingProcessingName()


def test_abc_prevents_instantiation_without_attribute_map():
    """ABC should prevent instantiation if ATTRIBUTE_MAP is not implemented."""

    class MissingAttributeMap(BTLxProcessing):
        PROCESSING_NAME = "MissingAttributeMap"

    with pytest.raises(TypeError, match=r"Can't instantiate abstract class MissingAttributeMap.*abstract method.*ATTRIBUTE_MAP"):
        MissingAttributeMap()


def test_abc_prevents_instantiation_without_both_abstract_properties():
    """ABC should prevent instantiation if neither abstract property is implemented."""

    class MissingBoth(BTLxProcessing):
        pass

    with pytest.raises(TypeError, match=r"Can't instantiate abstract class MissingBoth.*abstract methods.*ATTRIBUTE_MAP.*PROCESSING_NAME"):
        MissingBoth()


def test_valid_attribute_map_does_not_raise():
    # _ValidProcessing is defined at module level without error, confirming no raise at definition time
    processing = _ValidProcessing()
    assert processing is not None


def test_invalid_attribute_map_raises_at_definition_time():
    with pytest.raises(AttributeError, match="ATTRIBUTE_MAP in 'InvalidProcessing' references attributes not found"):

        class InvalidProcessing(BTLxProcessing):
            PROCESSING_NAME = "InvalidProcessing"
            ATTRIBUTE_MAP = {
                "StartX": "start_x",
                "Typo": "typo_attribute",  # this attribute does not exist on the class
            }

            @property
            def start_x(self):
                return 0.0


def test_error_message_contains_missing_attribute_name():
    with pytest.raises(AttributeError, match="typo_attribute"):

        class InvalidProcessing(BTLxProcessing):
            PROCESSING_NAME = "InvalidProcessing"
            ATTRIBUTE_MAP = {
                "Typo": "typo_attribute",
            }


def test_multiple_missing_attributes_all_reported():
    with pytest.raises(AttributeError) as exc_info:

        class MultiMissingProcessing(BTLxProcessing):
            PROCESSING_NAME = "MultiMissingProcessing"
            ATTRIBUTE_MAP = {
                "A": "missing_one",
                "B": "missing_two",
            }

    message = str(exc_info.value)
    assert "missing_one" in message
    assert "missing_two" in message


def test_subclass_without_attribute_map_does_not_raise():
    """Intermediate base classes that don't define ATTRIBUTE_MAP should not trigger the check."""

    class IntermediateProcessing(BTLxProcessing):
        PROCESSING_NAME = "IntermediateProcessing"
        ATTRIBUTE_MAP = {}  # Required by ABC to allow instantiation

    processing = IntermediateProcessing()
    assert processing is not None


def test_inherited_attribute_map_is_not_rechecked():
    """A subclass that inherits ATTRIBUTE_MAP without redefining it should not trigger the check."""

    class ChildProcessing(_ValidProcessing):
        pass

    processing = ChildProcessing()
    assert processing is not None
