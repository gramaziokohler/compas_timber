import pytest
from compas.geometry import Frame
from compas.tolerance import Tolerance
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication.btlx import BTLxProcessingParams
from compas_timber.errors import BTLxProcessingError
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


class MockProcessingParams(BTLxProcessingParams):
    """Mock processing params that raises ValueError when as_dict() is called."""

    def __init__(self, instance, should_raise=False, error_message="Test error"):
        super().__init__(instance)
        self._should_raise = should_raise
        self._error_message = error_message

    @property
    def attribute_map(self):
        return {"TestParam": "test_param"}

    def as_dict(self):
        if self._should_raise:
            raise ValueError(self._error_message)
        return {"test": "value"}


class MockProcessing(BTLxProcessing):
    PROCESSING_NAME = "MockProcessing"  # type: ignore

    def __init__(self, should_raise=False, error_message="Test error"):
        super().__init__()
        self._should_raise = should_raise
        self._error_message = error_message

    @property
    def params(self):
        return MockProcessingParams(self, self._should_raise, self._error_message)


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
    processing = MockProcessing(should_raise=True, error_message="Processing failed")
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert "Failed to create processing: Processing failed" in btlx_writer.errors[0].message


def test_model_to_xml_with_multiple_processing_errors(btlx_writer, mock_model):
    processing1 = MockProcessing(should_raise=True, error_message="Processing 1 failed")
    processing2 = MockProcessing(should_raise=True, error_message="Processing 2 failed")
    beam = list(mock_model.beams)[0]
    beam.add_features([processing1, processing2])

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 2
    assert all(isinstance(error, BTLxProcessingError) for error in btlx_writer.errors)
    assert any("Processing 1 failed" in error.message for error in btlx_writer.errors)
    assert any("Processing 2 failed" in error.message for error in btlx_writer.errors)


def test_model_to_xml_with_mixed_processing_results(btlx_writer, mock_model):
    processing1 = MockProcessing(should_raise=False)  # Success
    processing2 = MockProcessing(should_raise=True, error_message="Processing failed")  # Failure
    beam = list(mock_model.beams)[0]
    beam.add_features([processing1, processing2])

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert "Processing failed" in btlx_writer.errors[0].message


def test_model_to_xml_with_multiple_beams_and_errors(btlx_writer):
    model = TimberModel()

    # First beam with error
    beam1 = Beam(Frame.worldXY(), length=1000.0, width=100.0, height=100.0)
    processing1 = MockProcessing(should_raise=True, error_message="Beam 1 processing failed")
    beam1.add_features(processing1)
    model.add_element(beam1)

    # Second beam with error
    beam2 = Beam(Frame.worldXY(), length=800.0, width=80.0, height=80.0)
    processing2 = MockProcessing(should_raise=True, error_message="Beam 2 processing failed")
    beam2.add_features(processing2)
    model.add_element(beam2)

    result = btlx_writer.model_to_xml(model)

    assert result is not None
    assert len(btlx_writer.errors) == 2
    assert all(isinstance(error, BTLxProcessingError) for error in btlx_writer.errors)
    assert any("Beam 1 processing failed" in error.message for error in btlx_writer.errors)
    assert any("Beam 2 processing failed" in error.message for error in btlx_writer.errors)


def test_model_to_xml_with_different_error_messages(btlx_writer, mock_model):
    error_messages = ["Invalid parameter value", "Geometry calculation failed", "Reference side out of bounds", "Complex parameter serialization error"]

    beam = list(mock_model.beams)[0]
    processings = [MockProcessing(should_raise=True, error_message=msg) for msg in error_messages]
    beam.add_features(processings)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == len(error_messages)

    for i, error_msg in enumerate(error_messages):
        assert f"Failed to create processing: {error_msg}" in btlx_writer.errors[i].message


def test_write_method_preserves_errors(btlx_writer, mock_model, tmp_path):
    processing = MockProcessing(should_raise=True, error_message="Write test error")
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    file_path = tmp_path / "test.btlx"
    result = btlx_writer.write(mock_model, str(file_path))

    assert len(btlx_writer.errors) == 1
    assert isinstance(btlx_writer.errors[0], BTLxProcessingError)
    assert "Write test error" in btlx_writer.errors[0].message
    assert file_path.exists()
    assert result is not None


def test_model_to_xml_with_successful_processing(btlx_writer, mock_model):
    processing = MockProcessing(should_raise=False)
    beam = list(mock_model.beams)[0]
    beam.add_features(processing)

    result = btlx_writer.model_to_xml(mock_model)

    assert result is not None
    assert len(btlx_writer.errors) == 0
