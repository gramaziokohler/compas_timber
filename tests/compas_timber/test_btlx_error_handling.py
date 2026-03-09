import pytest
import warnings
from compas.geometry import Frame
from compas.tolerance import Tolerance
from compas_timber.btlx import BTLxReader
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import BTLxProcessing
from compas_timber.errors import BTLxProcessingError
from compas_timber.errors import BTLxParsingError
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
        self._unsupported_param = _UnsupportedType()

    @property
    def unsupported_param(self):
        return self._unsupported_param

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
        self._test_param = "test_value"

    @property
    def test_param(self):
        return self._test_param

    @property
    def __data__(self):
        data = super(MockProcessingSuccess, self).__data__
        data["test_param"] = self.test_param
        return data


@pytest.fixture
def btlx_writer():
    return BTLxWriter()


@pytest.fixture
def btlx_reader():
    return BTLxReader()


@pytest.fixture
def mock_model():
    model = TimberModel(Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(Beam(Frame.worldXY(), length=1000.0, width=100.0, height=100.0))
    return model


# =============================================================================
# BTLxWriter Error Handling Tests
# =============================================================================


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


# =============================================================================
# BTLxReader Error Handling Tests
# =============================================================================


class MinimalBTLxPart(object):
    """Generates minimal BTLx XML strings for use in reader tests."""

    TEMPLATE = """\
<?xml version="1.0"?>
<BTLx xmlns="https://www.design2machine.com">
  <Project Name="Test">
    <Parts>
      <Part Length="{length}" Width="{width}" Height="{height}"
            SingleMemberNumber="{single_member_number}" ElementNumber="test"
            Annotation="{annotation}" Designation="{designation}">
        <Transformations>
          <Transformation GUID="{{{guid}}}">
            <Position>
              <ReferencePoint X="0" Y="0" Z="0"/>
              <XVector X="1" Y="0" Z="0"/>
              <YVector X="0" Y="1" Z="0"/>
            </Position>
          </Transformation>
        </Transformations>
        {processings}
      </Part>
    </Parts>
  </Project>
</BTLx>"""

    WITH_TWO_PARTS_VALID = """\
<?xml version="1.0"?>
<BTLx xmlns="https://www.design2machine.com">
  <Project Name="Test">
    <Parts>
      <Part Length="bad" Width="100.0" Height="120.0" SingleMemberNumber="1" ElementNumber="1" Annotation="FailPart" Designation="Beam">
        <Transformations>
          <Transformation GUID="{11111111-1111-1111-1111-111111111111}">
            <Position>
              <ReferencePoint X="0" Y="0" Z="0"/>
              <XVector X="1" Y="0" Z="0"/>
              <YVector X="0" Y="1" Z="0"/>
            </Position>
          </Transformation>
        </Transformations>
      </Part>
      <Part Length="1000.0" Width="100.0" Height="120.0" SingleMemberNumber="2" ElementNumber="2" Annotation="GoodPart" Designation="Beam">
        <Transformations>
          <Transformation GUID="{22222222-2222-2222-2222-222222222222}">
            <Position>
              <ReferencePoint X="0" Y="0" Z="0"/>
              <XVector X="1" Y="0" Z="0"/>
              <YVector X="0" Y="1" Z="0"/>
            </Position>
          </Transformation>
        </Transformations>
      </Part>
    </Parts>
  </Project>
</BTLx>"""

    @classmethod
    def build(cls, length, width, height, single_member_number, annotation, designation, guid, processings=""):
        return cls.TEMPLATE.format(
            length=length,
            width=width,
            height=height,
            single_member_number=single_member_number,
            annotation=annotation,
            designation=designation,
            guid=guid,
            processings=processings,
        )

    @classmethod
    def valid(cls):
        return cls.build(
            length="1000.0",
            width="100.0",
            height="120.0",
            single_member_number="1",
            annotation="Beam_01",
            designation="Beam",
            guid="12345678-1234-1234-1234-123456789ABC",
            processings="",
        )


def test_btlx_parsing_error_fields():
    """Test that BTLxParsingError stores part_id and processing_type correctly."""
    err = BTLxParsingError("something went wrong", part_id="Beam_01", processing_type="JackRafterCut")
    assert err.part_id == "Beam_01"
    assert err.processing_type == "JackRafterCut"
    assert err.message == "something went wrong"


def test_btlx_reader_unsupported_processing_sets_processing_type(btlx_reader):
    """BTLxParsingError for unsupported processing must carry processing_type."""
    xml = MinimalBTLxPart.build(
        length="1000.0",
        width="100.0",
        height="120.0",
        single_member_number="1",
        annotation="Beam_01",
        designation="Beam",
        guid="12345678-1234-1234-1234-123456789ABC",
        processings="<Processings><GhostCut/></Processings>",
    )
    with pytest.warns(UserWarning, match="1 error"):
        model = btlx_reader.xml_to_model(xml)

    assert isinstance(model, TimberModel)
    assert len(btlx_reader.errors) == 1
    error = btlx_reader.errors[0]
    assert isinstance(error, BTLxParsingError)
    assert error.processing_type == "GhostCut"
    assert error.part_id == "1"

    # Despite the processing error, the part should still be added to the model
    assert len(list(model.beams)) == 1
    assert list(model.beams)[0].name == "Beam_01"


def test_btlx_reader_bad_dimensions_raises_fatal_part_error(btlx_reader):
    """A part with a non-numeric dimension must be skipped and the error collected."""
    xml = MinimalBTLxPart.build(
        length="not_a_number",
        width="100.0",
        height="120.0",
        single_member_number="7",
        annotation="BadBeam",
        designation="Beam",
        guid="12345678-1234-1234-1234-123456789ABC",
        processings="",
    )
    with pytest.warns(UserWarning, match="1 error"):
        model = btlx_reader.xml_to_model(xml)

    assert len(list(model.beams)) == 0
    assert len(btlx_reader.errors) == 1
    error = btlx_reader.errors[0]
    assert isinstance(error, BTLxParsingError)
    assert error.part_id == "7"


def test_btlx_reader_bad_part_does_not_stop_other_parts(btlx_reader):
    """A failing part must not prevent subsequent parts from being parsed."""

    with pytest.warns(UserWarning, match="1 error"):
        xml = MinimalBTLxPart.WITH_TWO_PARTS_VALID
        model = btlx_reader.xml_to_model(xml)

    assert len(list(model.beams)) == 1
    assert list(model.beams)[0].name == "GoodPart"
    assert len(btlx_reader.errors) == 1
    assert btlx_reader.errors[0].part_id == "1"


def test_btlx_reader_warn_issued_when_errors_present(btlx_reader):
    """xml_to_model must issue a UserWarning when errors are collected."""
    xml = MinimalBTLxPart.build(
        length="1000.0",
        width="100.0",
        height="120.0",
        single_member_number="5",
        annotation="Beam_01",
        designation="Beam",
        guid="12345678-1234-1234-1234-123456789ABC",
        processings="<Processings><GhostCut/></Processings>",
    )
    with pytest.warns(UserWarning, match="error"):
        btlx_reader.xml_to_model(xml)


def test_btlx_reader_no_warn_when_no_errors(btlx_reader):
    """xml_to_model must not issue a UserWarning when parsing succeeds cleanly."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        btlx_reader.xml_to_model(MinimalBTLxPart.valid())

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0


def test_btlx_reader_print_errors_no_errors(capsys, btlx_reader):
    btlx_reader.print_errors()
    assert capsys.readouterr().out.strip() == "No errors."


def test_btlx_reader_print_errors_with_errors(capsys, btlx_reader):
    xml = MinimalBTLxPart.build(
        length="1000.0",
        width="100.0",
        height="120.0",
        single_member_number="5",
        annotation="Beam_01",
        designation="Beam",
        guid="12345678-1234-1234-1234-123456789ABC",
        processings="<Processings><GhostCut/></Processings>",
    )
    with pytest.warns(UserWarning):
        btlx_reader.xml_to_model(xml)
    btlx_reader.print_errors()
    output = capsys.readouterr().out
    assert "1 error(s)" in output
    assert "GhostCut" in output
