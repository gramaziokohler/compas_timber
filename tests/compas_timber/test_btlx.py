import os
import pytest
from unittest.mock import patch

from compas.data import json_load
from compas.tolerance import Tolerance
from compas.geometry import Frame

import xml.etree.ElementTree as ET

import compas
import compas_timber
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import BTLxPart
from compas_timber.fabrication import BTLxRawpart
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import OrientationType
from compas_timber.elements import Beam
from compas_timber.elements import CutFeature
from compas_timber.model import TimberModel
from compas_timber.planning import BeamStock
from compas_timber.planning import NestingResult


@pytest.fixture(scope="module")
def test_model():
    model_path = os.path.join(compas_timber.DATA, "model_test.json")
    model = json_load(model_path)
    with patch("compas_timber.connections.Joint.add_features"):
        model.process_joinery()
    return model


@pytest.fixture(scope="module")
def expected_btlx():
    btlx_path = os.path.join(compas_timber.DATA, "model_test.btlx")
    with open(btlx_path, "r", encoding="utf-8") as btlx:
        return ET.fromstring(btlx.read())


@pytest.fixture(scope="module")
def resulting_btlx(test_model):
    writer = BTLxWriter()
    resulting_btlx_str = writer.model_to_xml(test_model)
    return ET.fromstring(resulting_btlx_str)


@pytest.fixture
def namespaces():
    return {"d2m": "https://www.design2machine.com"}


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_btlx_file_history(resulting_btlx, namespaces):
    # Validate the FileHistory element
    file_history = resulting_btlx.find("d2m:FileHistory", namespaces)
    assert file_history is not None

    # Validate the InitialExportProgram element within FileHistory
    initial_export_program = file_history.find("d2m:InitialExportProgram", namespaces)
    assert initial_export_program is not None

    # Validate the attributes of InitialExportProgram
    assert initial_export_program.get("CompanyName") == "Gramazio Kohler Research"
    assert initial_export_program.get("ProgramName") == "COMPAS_Timber"
    assert initial_export_program.get("ProgramVersion") == "Compas: {}".format(compas.__version__)
    assert initial_export_program.get("ComputerName") == (os.getenv("computername") or "None")
    assert initial_export_program.get("UserName") == (os.getenv("USERNAME") or "None")


def test_btlx_parts(resulting_btlx, test_model, namespaces):
    # Find the Project element
    project = resulting_btlx.find("d2m:Project", namespaces)
    assert project is not None

    # Find the Parts element within the Project element
    parts = project.find("d2m:Parts", namespaces)
    assert parts is not None

    # Find all Part elements within the Parts element
    part_elements = parts.findall("d2m:Part", namespaces)
    assert len(part_elements) == len(test_model.beams)

    # Validate each Part element
    for i, (part, beam) in enumerate(zip(part_elements, test_model.beams)):
        assert part.get("Length") == "{:.3f}".format(beam.blank_length)
        assert part.get("Height") == "{:.3f}".format(beam.height)
        assert part.get("Width") == "{:.3f}".format(beam.width)
        assert part.get("OrderNumber") == str(i)
        assert part.get("ElementNumber") == str(beam.guid)[:4]
        assert part.get("Annotation") == f"{beam.name}-{str(beam.guid)[:4]}"


def test_btlx_processings(resulting_btlx, test_model, namespaces):
    # Find the Project element
    project = resulting_btlx.find("d2m:Project", namespaces)
    assert project is not None

    # Find the Parts element within the Project element
    parts = project.find("d2m:Parts", namespaces)
    assert parts is not None

    # Find all Part elements within the Parts element
    part_elements = parts.findall("d2m:Part", namespaces)
    assert len(part_elements) == len(test_model.beams)

    # Validate the features and processings
    for part, beam in zip(part_elements, test_model.beams):
        beam_features = beam.features
        processings = part.find("d2m:Processings", namespaces)
        if processings:
            assert len(processings) == len(beam_features)
        else:
            assert processings is None and len(beam_features) == 0


def test_expected_btlx(resulting_btlx, expected_btlx, namespaces):
    # Validate the root element
    assert resulting_btlx.tag == expected_btlx.tag

    # Validate the FileHistory element
    resulting_file_history = resulting_btlx.find("d2m:FileHistory", namespaces)
    expected_file_history = expected_btlx.find("d2m:FileHistory", namespaces)
    assert resulting_file_history is not None
    assert expected_file_history is not None
    assert resulting_file_history.tag == expected_file_history.tag

    # Validate the Project element
    resulting_project = resulting_btlx.find("d2m:Project", namespaces)
    expected_project = expected_btlx.find("d2m:Project", namespaces)
    assert resulting_project is not None
    assert expected_project is not None
    assert resulting_project.tag == expected_project.tag

    # Validate the Parts element within the Project element
    resulting_parts = resulting_project.find("d2m:Parts", namespaces)
    expected_parts = expected_project.find("d2m:Parts", namespaces)
    assert resulting_parts is not None
    assert expected_parts is not None
    assert resulting_parts.tag == expected_parts.tag

    # Validate all Part elements within the Parts element
    resulting_part_elements = resulting_parts.findall("d2m:Part", namespaces)
    expected_part_elements = expected_parts.findall("d2m:Part", namespaces)
    assert len(resulting_part_elements) == len(expected_part_elements)

    for resulting_part, expected_part in zip(resulting_part_elements, expected_part_elements):
        # Validate the Processings element within each Part element
        resulting_processings = resulting_part.find("d2m:Processings", namespaces)
        expected_processings = expected_part.find("d2m:Processings", namespaces)
        if resulting_processings and expected_processings:
            assert resulting_processings.tag == expected_processings.tag
            # Validate all Processing elements within the Processings element
            resulting_processing_elements = resulting_processings.findall("d2m:Processing", namespaces)
            expected_processing_elements = expected_processings.findall("d2m:Processing", namespaces)
            assert len(resulting_processing_elements) == len(expected_processing_elements)
            # Validate each Processing element
            for resulting_processing, expected_processing in zip(resulting_processing_elements, expected_processing_elements):
                assert resulting_processing.tag == expected_processing.tag
                assert resulting_processing.attrib == expected_processing.attrib
        else:
            # If Processings is None in either, they should both be None
            assert resulting_processings == expected_processings


def test_btlx_should_skip_feature():
    writer = BTLxWriter()
    model = TimberModel()
    beam = Beam(Frame.worldXY(), 1000, 100, 100)
    beam.add_features(CutFeature(Frame.worldXY()))
    model.add_element(beam)

    with pytest.warns():
        result = writer.model_to_xml(model)

    assert result is not None


def test_float_formatting_of_param_dicts():
    test_processing = JackRafterCut(OrientationType.END, 10, 20.0, 0.5, 45.000, 90, ref_side_index=1)
    params_dict = test_processing.params.as_dict()

    assert params_dict["Orientation"] == "end"
    assert params_dict["StartX"] == "{:.3f}".format(test_processing.start_x)
    assert params_dict["StartY"] == "{:.3f}".format(test_processing.start_y)
    assert params_dict["StartDepth"] == "{:.3f}".format(test_processing.start_depth)
    assert params_dict["Angle"] == "{:.3f}".format(test_processing.angle)
    assert params_dict["Inclination"] == "{:.3f}".format(test_processing.inclination)
    assert test_processing.params.header_attributes["ReferencePlaneID"] == "{:.0f}".format(test_processing.ref_side_index + 1)


def test_processing_scaled_called_for_meter_units(mocker):
    writer = BTLxWriter()
    model = TimberModel(Tolerance(unit="M", absolute=1e-3, relative=1e-3))
    beam = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    processing = JackRafterCut(OrientationType.END, 0.01, 0.02, 0.005, 45.0, 90.0, ref_side_index=0)
    beam.add_features(processing)
    model.add_element(beam)

    spy = mocker.spy(processing, "scaled")
    writer.model_to_xml(model)
    spy.assert_called_once_with(1000.0)


def test_processing_scaled_not_called_for_millimeter_units(mocker):
    writer = BTLxWriter()
    model = TimberModel(Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    beam = Beam(Frame.worldXY(), length=1000.0, width=100.0, height=100.0)
    processing = JackRafterCut(OrientationType.END, 10.0, 20.0, 5.0, 45.0, 90.0, ref_side_index=0)
    beam.add_features(processing)
    model.add_element(beam)

    spy = mocker.spy(processing, "scaled")
    writer.model_to_xml(model)
    spy.assert_not_called()


def test_BTLxPart_GUID_is_the_same_as_Beam_GUID(test_model, resulting_btlx, namespaces):
    # Find the Project element
    project = resulting_btlx.find("d2m:Project", namespaces)
    assert project is not None

    # Find the Parts element within the Project element
    parts = project.find("d2m:Parts", namespaces)
    assert parts is not None

    # Find all Part elements within the Parts element
    part_elements = parts.findall("d2m:Part", namespaces)
    assert len(part_elements) == len(list(test_model.beams))

    # Validate each Part element's GUID matches the corresponding Beam's GUID
    for part, beam in zip(part_elements, test_model.beams):
        # Find the Transformations element within the Part
        transformations = part.find("d2m:Transformations", namespaces)
        assert transformations is not None

        # Find the Transformation element within Transformations
        transformation = transformations.find("d2m:Transformation", namespaces)
        assert transformation is not None

        # Get the GUID from the Transformation element
        part_guid = transformation.get("GUID")
        assert part_guid == "{" + str(beam.guid) + "}"


def test_btlx_with_nesting_result_creates_rawparts(namespaces):
    """Test that BTLx writer creates rawpart elements when nesting_result is provided."""
    # Create a simple model with two beams
    model = TimberModel()
    beam1 = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam2 = Beam(Frame.worldXY(), length=800, width=100, height=100)
    model.add_element(beam1)
    model.add_element(beam2)

    # Create stock and assign beams
    stock = BeamStock(length=2000, cross_section=(100, 100))
    stock.add_element(beam1)
    stock.add_element(beam2)

    # Create nesting result
    nesting_result = NestingResult([stock])

    # Generate BTLx with nesting result
    writer = BTLxWriter()
    btlx_str = writer.model_to_xml(model, nesting_result)
    btlx_root = ET.fromstring(btlx_str)

    # Find the Project element
    project = btlx_root.find("d2m:Project", namespaces)
    assert project is not None

    # Check that rawparts element exists
    rawparts = project.find("d2m:Rawparts", namespaces)
    assert rawparts is not None

    # Check that one rawpart was created
    rawpart_elements = rawparts.findall("d2m:Rawpart", namespaces)
    assert len(rawpart_elements) == 1

    # Validate rawpart properties
    rawpart = rawpart_elements[0]
    assert rawpart.get("Length") == "2000.000"
    assert rawpart.get("Width") == "100.000"
    assert rawpart.get("Height") == "100.000"


def test_btlx_rawpart_contains_correct_part_references(namespaces):
    """Test that rawpart elements contain correct part references with positioning."""
    # Create a simple model with one beam
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=500, width=80, height=120)
    model.add_element(beam)

    # Create stock and assign beam
    stock = BeamStock(length=1000, cross_section=(80, 120))
    stock.add_element(beam)

    # Create nesting result
    nesting_result = NestingResult([stock])

    # Generate BTLx with nesting result
    writer = BTLxWriter()
    btlx_str = writer.model_to_xml(model, nesting_result)
    btlx_root = ET.fromstring(btlx_str)

    # Find the rawpart
    project = btlx_root.find("d2m:Project", namespaces)
    rawparts = project.find("d2m:Rawparts", namespaces)
    rawpart = rawparts.find("d2m:Rawpart", namespaces)

    # Check part references
    part_refs = rawpart.find("d2m:PartRefs", namespaces)
    assert part_refs is not None

    part_ref_elements = part_refs.findall("d2m:PartRef", namespaces)
    assert len(part_ref_elements) == 1

    # Validate part reference properties
    part_ref = part_ref_elements[0]
    assert part_ref.get("GUID") == "{" + str(beam.guid) + "}"

    # Check that position exists for positioning (not transformations)
    position = part_ref.find("d2m:Position", namespaces)
    assert position is not None

    # Validate position contains required elements
    ref_point = position.find("d2m:ReferencePoint", namespaces)
    assert ref_point is not None

    x_vector = position.find("d2m:XVector", namespaces)
    assert x_vector is not None

    y_vector = position.find("d2m:YVector", namespaces)
    assert y_vector is not None


def test_btlx_generic_part_inheritance():
    """Test that BTLxPart and BTLxRawpart both inherit from BTLxGenericPart."""
    # Create a beam and stock for testing
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    stock = BeamStock(length=2000, cross_section=(100, 100))

    # Create instances of both subclasses
    btlx_part = BTLxPart(beam, order_num=1)
    btlx_rawpart = BTLxRawpart(stock, order_number=2)

    for part in [btlx_part, btlx_rawpart]:
        # Test common properties exist
        assert hasattr(part, "length")
        assert hasattr(part, "width")
        assert hasattr(part, "height")
        assert hasattr(part, "order_num")
        # Test common methods exist
        assert hasattr(part, "et_point_vals")
        assert hasattr(part, "et_grain_direction")
        assert hasattr(part, "et_reference_side")
        assert hasattr(part, "et_transformations")


def test_btlx_part_unique_functionalities():
    """Test BTLxPart unique functionalities for fabricated parts."""
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    btlx_part = BTLxPart(beam, order_num=1)

    # Test element reference
    assert hasattr(btlx_part, "element")
    assert btlx_part.element == beam

    # Test processings list for fabrication operations
    assert hasattr(btlx_part, "processings")
    assert isinstance(btlx_part.processings, list)


def test_btlx_rawpart_unique_functionalities():
    """Test BTLxRawpart unique functionalities for raw material parts."""
    stock = BeamStock(length=2000, cross_section=(100, 100))
    btlx_rawpart = BTLxRawpart(stock, order_number=2)

    # Test stock reference
    assert hasattr(btlx_rawpart, "stock")
    assert btlx_rawpart.stock == stock

    # Test part references for nesting functionality
    assert hasattr(btlx_rawpart, "part_refs")
    assert isinstance(btlx_rawpart.part_refs, list)
    assert hasattr(btlx_rawpart, "add_part_ref")
    assert hasattr(btlx_rawpart, "et_part_refs")

    # Test rawpart-specific attributes
    btlx_rawpart_attr = btlx_rawpart.attr
    assert "PlaningLength" in btlx_rawpart_attr
    assert "StartOffset" in btlx_rawpart_attr
    assert "EndOffset" in btlx_rawpart_attr
    assert btlx_rawpart_attr["PlaningLength"] == "0"
    assert btlx_rawpart_attr["StartOffset"] == "0"
    assert btlx_rawpart_attr["EndOffset"] == "0"

    # Test add_part_ref functionality
    test_guid = "test-guid-123"
    test_frame = Frame.worldXY()
    btlx_rawpart.add_part_ref(test_guid, test_frame)
    assert len(btlx_rawpart.part_refs) == 1
    assert btlx_rawpart.part_refs[0]["guid"] == test_guid
    assert btlx_rawpart.part_refs[0]["frame"] == test_frame


def test_rawpart_attributes():
    """Test that BTLxRawpart has correct attributes and GUID handling."""
    stock = BeamStock(length=2000, cross_section=(100, 100))
    # Assign a specific name to the stock for testing
    stock.name = "TestStock"
    rawpart = BTLxRawpart(stock, order_number=7)

    # Check basic attributes
    assert rawpart.length == 2000
    assert rawpart.width == 100
    assert rawpart.height == 100
    assert rawpart.order_num == 7

    # Check GUID generation and format
    assert hasattr(rawpart, "part_guid")
    assert isinstance(rawpart.part_guid, str)

    # Check ElementNumber and Annotation
    base_attr = rawpart.base_attr
    assert base_attr["OrderNumber"] == "7"
    assert base_attr["ElementNumber"] == rawpart.part_guid[:4]
    assert base_attr["Annotation"] == "TestStock-{}".format(rawpart.part_guid[:4])
