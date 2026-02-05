import pytest
from compas.geometry import Frame
from compas.tolerance import Tolerance
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import BTLxProcessing
from compas_timber.errors import BTLxProcessingError
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


class _UnsupportedType:
    """A type that is not supported by BTLxProcessingParams._format_value()."""

    pass


class MockProcessingWithBadAttribute(BTLxProcessing):
    """Mock processing where accessing an attribute raises an error.

    This simulates errors that occur during serialization when trying to
    access processing attributes referenced in ATTRIBUTE_MAP.
    """

    PROCESSING_NAME = "MockProcessingWithBadAttribute"
    ATTRIBUTE_MAP = {"BadParam": "bad_param"}

    def __init__(self, error_message="Test error"):
        super(MockProcessingWithBadAttribute, self).__init__()
        self._error_message = error_message

    @property
    def __data__(self):
        data = super(MockProcessingWithBadAttribute, self).__data__
        # Don't include bad_param in data since it will raise
        return data

    @property
    def bad_param(self):
        """Property that raises ValueError when accessed."""
        raise ValueError(self._error_message)


class MockProcessingWithUnsupportedType(BTLxProcessing):
    """Mock processing with an attribute that has an unsupported type.

    This simulates errors when _format_value() encounters a type that is not:
    - A primitive (str, int, float, bool)
    - MachiningLimits
    - Registered in BTLxWriter.SERIALIZERS
    """

    PROCESSING_NAME = "MockProcessingWithUnsupportedType"
    ATTRIBUTE_MAP = {"UnsupportedParam": "unsupported_param"}

    def __init__(self):
        super(MockProcessingWithUnsupportedType, self).__init__()
        self.unsupported_param = _UnsupportedType()

    @property
    def __data__(self):
        data = super(MockProcessingWithUnsupportedType, self).__data__
        # Can't serialize unsupported_param in data either
        return data


class MockProcessingSuccess(BTLxProcessing):
    """Mock processing that serializes successfully."""

    PROCESSING_NAME = "MockProcessingSuccess"
    ATTRIBUTE_MAP = {"TestParam": "test_param"}

    def __init__(self):
        super(MockProcessingSuccess, self).__init__()
        self.test_param = "test_value"

    @property
    def __data__(self):
        data = super(MockProcessingSuccess, self).__data__
        data["test_param"] = self.test_param
        return data


@pytest.fixture
def btlx_writer():
    return BTLxWriter()


@pytest.fixture
def mock_model():
    model = TimberModel(Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(Beam(Frame.worldXY(), length=1000.0, width=100.0, height=100.0))
    return model


def test_btlx_writer_initialization(btlx_writer):
    assert btlx_writer.errors == []


def test_model_to_xml_clears_errors_on_start(btlx_writer, mock_model):
    btlx_writer._errors = [BTLxProcessingError("Test error", object(), object())]
    result = btlx_writer.model_to_xml(mock_model)
    assert btlx_writer.errors == []
    assert result is not None


def test_model_to_xml_with_processing_error(btlx_writer, mock_model):
    """Test that errors during attribute access are caught and reported."""
    processing = MockProcessingWithBadAttribute(error_message="Processing failed")
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert "Failed to create processing" in btlx_writer.errors[0].message


def test_model_to_xml_with_multiple_processing_errors(btlx_writer, mock_model):
    """Test that multiple processing errors are all caught and reported."""
    processing1 = MockProcessingWithBadAttribute(error_message="Processing 1 failed")
    processing2 = MockProcessingWithBadAttribute(error_message="Processing 2 failed")
    beam = list(mock_model.beams)[0]
    beam.add_features([processing1, processing2])

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 2
    assert all(isinstance(error, BTLxProcessingError) for error in btlx_writer.errors)


def test_model_to_xml_with_mixed_processing_results(btlx_writer, mock_model):
    """Test that successful processings don't interfere with error reporting."""
    processing1 = MockProcessingSuccess()  # Success
    processing2 = MockProcessingWithBadAttribute(error_message="Processing failed")  # Failure
    beam = list(mock_model.beams)[0]
    beam.add_features([processing1, processing2])

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)


def test_model_to_xml_with_multiple_beams_and_errors(btlx_writer):
    """Test error handling across multiple beams."""
    model = TimberModel()

    # First beam with error
    beam1 = Beam(Frame.worldXY(), length=1000.0, width=100.0, height=100.0)
    processing1 = MockProcessingWithBadAttribute(error_message="Beam 1 processing failed")
    beam1.add_features(processing1)
    model.add_element(beam1)

    # Second beam with error
    beam2 = Beam(Frame.worldXY(), length=800.0, width=80.0, height=80.0)
    processing2 = MockProcessingWithBadAttribute(error_message="Beam 2 processing failed")
    beam2.add_features(processing2)
    model.add_element(beam2)

    result = btlx_writer.model_to_xml(model)

    assert result is not None
    assert len(btlx_writer.errors) == 2
    assert all(isinstance(error, BTLxProcessingError) for error in btlx_writer.errors)


def test_model_to_xml_with_unsupported_type_error(btlx_writer, mock_model):
    """Test that unsupported value types are caught and reported."""
    processing = MockProcessingWithUnsupportedType()
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert "Failed to create processing" in btlx_writer.errors[0].message


def test_model_to_xml_with_different_error_types(btlx_writer, mock_model):
    """Test that different types of serialization errors are all caught."""
    beam = list(mock_model.beams)[0]
    processings = [
        MockProcessingWithBadAttribute(error_message="Attribute access error"),
        MockProcessingWithUnsupportedType(),
        MockProcessingWithBadAttribute(error_message="Another attribute error"),
    ]
    beam.add_features(processings)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 3
    assert all(isinstance(error, BTLxProcessingError) for error in btlx_writer.errors)


def test_write_method_preserves_errors(btlx_writer, mock_model, tmp_path):
    """Test that write() method preserves error information."""
    processing = MockProcessingWithBadAttribute(error_message="Write test error")
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    file_path = tmp_path / "test.btlx"
    result = btlx_writer.write(mock_model, str(file_path))

    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert file_path.exists()
    assert result is not None


def test_model_to_xml_with_successful_processing(btlx_writer, mock_model):
    """Test that successful processings don't generate errors."""
    processing = MockProcessingSuccess()
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 0
