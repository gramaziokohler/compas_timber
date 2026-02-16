import os
import pytest
from unittest.mock import patch

from compas.data import json_load
from compas.tolerance import Tolerance
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline

import xml.etree.ElementTree as ET

import compas
import compas_timber
from compas_timber.btlx import BTLxReader
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import BTLxPart
from compas_timber.fabrication import BTLxRawpart
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import OrientationType
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import Contour
from compas_timber.fabrication import DualContour
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel
from compas_timber.planning import BeamStock
from compas_timber.planning import NestingResult
from compas.tolerance import TOL


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
        assert part.get("Annotation") == f"{beam.name}"


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
    assert base_attr["Annotation"] == stock.name


# =============================================================================
# BTLxReader Tests
# =============================================================================


def test_btlx_model_roundtrip(tol):
    """Test that writing and reading produces equivalent model."""
    # Create simple model
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=120)
    beam.name = "test_beam"
    model.add_element(beam)

    # Write to XML string
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)

    # Read back
    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify
    assert len(model_read.beams) == 1
    beam_read = model_read.beams[0]
    assert beam_read.name == "test_beam"
    assert tol.is_close(beam_read.length, 1000)
    assert tol.is_close(beam_read.width, 100)
    assert tol.is_close(beam_read.height, 120)
    assert beam_read.guid == beam.guid


def test_btlx_transformation_roundtrip(tol):
    """Test that BTLx read/write roundtrip preserves exact transformations."""
    model = TimberModel()

    # Create a beam with non-trivial orientation
    beam_original = Beam(Frame([2000, -60, 1000], [-1, 0, 0], [0, 0, 1]), length=1500, width=120, height=120)
    beam_original.name = "test_beam"
    model.add_element(beam_original)

    # Write to BTLx and read back
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)

    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify beam was read
    assert len(model_read.beams) == 1
    beam_read = model_read.beams[0]

    # Check dimensions
    assert tol.is_close(beam_original.length, beam_read.length)
    assert tol.is_close(beam_original.width, beam_read.width)
    assert tol.is_close(beam_original.height, beam_read.height)

    # Check centerline frame (origin and axes)
    assert tol.is_allclose(beam_original.frame.point, beam_read.frame.point)
    assert tol.is_allclose(beam_original.frame.xaxis, beam_read.frame.xaxis)
    assert tol.is_allclose(beam_original.frame.yaxis, beam_read.frame.yaxis)

    # Check ref_frame (BTLx reference frame) - this is what gets written to BTLx
    # If centerline frame is preserved, ref_frame should also match
    assert tol.is_allclose(beam_original.ref_frame.point, beam_read.ref_frame.point)
    assert tol.is_allclose(beam_original.ref_frame.yaxis, beam_read.ref_frame.yaxis)


def test_btlx_reader_beam_and_plate():
    """Test that both Beam and Plate elements are correctly read."""
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=120)
    plate = Plate(Frame.worldXY(), length=2000, width=500, thickness=20)
    beam.name = "my_beam"
    plate.name = "my_plate"
    model.add_element(beam)
    model.add_element(plate)

    # Roundtrip
    xml_string = BTLxWriter().model_to_xml(model)
    model_read = BTLxReader().xml_to_model(xml_string)

    # Verify counts and types
    assert len(model_read.beams) == 1
    assert len(model_read.plates) == 1
    assert model_read.beams[0].name == "my_beam"
    assert model_read.plates[0].name == "my_plate"


def test_btlx_reader_with_processings():
    """Test that a BTLx file with processings is read correctly."""
    # 1. Create a model with a beam and a feature
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=120)
    beam.name = "beam_with_cut"

    original_feature = JackRafterCut(orientation=OrientationType.END, start_x=50.0, start_y=10.0, start_depth=20.0, angle=45.0, inclination=30.0)
    beam.features.append(original_feature)
    model.add_element(beam)

    # 2. Write to XML string
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)

    # 3. Read back
    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # 4. Assertions
    assert len(model_read.beams) == 1
    beam_read = model_read.beams[0]
    assert beam_read.name == "beam_with_cut"

    assert len(beam_read.features) == 1
    feature_read = beam_read.features[0]

    assert isinstance(feature_read, JackRafterCut)

    # Workaround for comparing float values with tolerance
    assert feature_read.orientation == original_feature.orientation
    assert TOL.is_close(feature_read.start_x, original_feature.start_x)
    assert TOL.is_close(feature_read.start_y, original_feature.start_y)
    assert TOL.is_close(feature_read.start_depth, original_feature.start_depth)
    assert TOL.is_close(feature_read.angle, original_feature.angle)
    assert TOL.is_close(feature_read.inclination, original_feature.inclination)


@pytest.mark.parametrize(
    "dimensions, expected_type",
    [
        ((100, 100, 5000), "Beam"),  # Classic beam
        ((5000, 100, 100), "Beam"),  # Classic beam, different order
        ((100, 5000, 100), "Beam"),  # Classic beam, different order
        ((2000, 1000, 50), "Plate"),  # Classic plate
        ((50, 2000, 1000), "Plate"),  # Classic plate, different order
        ((1000, 50, 2000), "Plate"),  # Classic plate, different order
        ((1000, 800, 600), "Beam"),  # Chunky beam, fails plate criteria
        ((300, 300, 300), "Beam"),  # A cube, defaults to beam
        ((3000, 650, 200), "Beam"),  # Closer ratio, but still a beam (3000/650 < 5)
        ((3000, 700, 100), "Plate"),  # d1/d2 < 5 and d2/d3 > 5
    ],
)
def test_infer_element_type(dimensions, expected_type):
    """Test the logic for inferring element type from dimensions."""
    reader = BTLxReader()
    width, height, length = dimensions
    element_type = reader._infer_element_type(width, height, length)
    assert element_type == expected_type


def test_btlx_reader_full_file(test_model, tol):
    """Test that a full BTLx file is read correctly and matches a reference model."""
    btlx_path = os.path.join(compas_timber.DATA, "model_test.btlx")
    reader = BTLxReader()
    model_read = reader.read(btlx_path)

    assert isinstance(model_read, TimberModel)
    assert len(model_read.beams) == len(test_model.beams)

    # Create a dictionary for the original beams for easy lookup
    original_beams_map = {str(beam.guid): beam for beam in test_model.beams}

    # Check for parsing errors
    assert reader.errors == [], f"Errors encountered during BTLx reading: {reader.errors}"

    # Check properties of each read beam against its original counterpart
    for beam_read in model_read.beams:
        beam_original = original_beams_map.get(str(beam_read.guid))
        assert beam_original is not None, f"Beam with GUID {beam_read.guid} not found in original model."

        # assert beam_read.name == beam_original.name
        assert tol.is_close(beam_read.length, beam_original.blank_length)
        assert tol.is_close(beam_read.width, beam_original.width)
        assert tol.is_close(beam_read.height, beam_original.height)
        assert beam_read.guid == beam_original.guid

        # Check that processings were created
        assert len(beam_read.features) == len(beam_original.features)


def test_btlx_reader_free_contour_with_simple_contour_roundtrip(tol):
    """Test that FreeContour with simple Contour parameters survives roundtrip."""
    model = TimberModel()

    # Create a plate
    plate = Plate(Frame.worldXY(), length=1000, width=500, thickness=20)
    plate.name = "test_plate"

    # Create FreeContour with simple Contour (single inclination)
    polyline = Polyline([Point(10, 10, 0), Point(490, 10, 0), Point(490, 490, 0), Point(10, 490, 0), Point(10, 10, 0)])
    contour = Contour(polyline=polyline, depth=15.0, depth_bounded=True, inclination=[45.0])
    free_contour = FreeContour(contour)
    plate.add_features(free_contour)
    model.add_element(plate)

    # Write to BTLx and read back
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)

    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify no parsing errors
    assert len(reader.errors) == 0, f"Errors encountered during BTLx reading: {reader.errors}"

    # Verify plate was read
    assert len(model_read.plates) == 1
    plate_read = model_read.plates[0]
    assert plate_read.name == "test_plate"

    # Verify features were read (plate will have outline + our added feature = 2 total)
    # But we only added 1 feature to the original plate, so after roundtrip we expect that same feature count
    assert len(plate_read.features) >= 1

    # Find the feature we added (it should be the last one or one with matching depth)
    feature_read = None
    for f in plate_read.features:
        if isinstance(f, FreeContour) and isinstance(f.contour_param_object, Contour):
            if TOL.is_close(f.contour_param_object.depth, 15.0):
                feature_read = f
                break

    assert feature_read is not None, "Could not find the FreeContour with depth 15.0"

    # Verify Contour parameter object
    assert isinstance(feature_read.contour_param_object, Contour)
    assert tol.is_close(feature_read.contour_param_object.depth, 15.0)
    assert feature_read.contour_param_object.depth_bounded is True
    assert len(feature_read.contour_param_object.inclination) == 4  # 4 segments in closed polyline
    assert tol.is_close(feature_read.contour_param_object.inclination[0], 45.0)


def test_btlx_reader_free_contour_with_multiple_inclinations_roundtrip(tol):
    """Test that FreeContour with per-segment inclinations survives roundtrip."""
    model = TimberModel()

    # Create a plate
    plate = Plate(Frame.worldXY(), length=1000, width=500, thickness=20)

    # Create FreeContour with per-segment inclinations
    polyline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 100, 0), Point(0, 0, 0)])
    contour = Contour(polyline=polyline, depth=10.0, depth_bounded=True, inclination=[30.0, 45.0, 60.0, 90.0])
    free_contour = FreeContour(contour)
    plate.add_features(free_contour)
    model.add_element(plate)

    # Roundtrip
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)
    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify
    assert len(reader.errors) == 0
    plate_read = model_read.plates[0]

    # Find the feature with per-segment inclinations
    feature_read = None
    for f in plate_read.features:
        if isinstance(f, FreeContour) and isinstance(f.contour_param_object, Contour):
            if len(f.contour_param_object.inclination) == 4:
                # Check if inclinations match
                incl = f.contour_param_object.inclination
                if tol.is_close(incl[0], 30.0) and tol.is_close(incl[1], 45.0):
                    feature_read = f
                    break

    assert feature_read is not None, "Could not find FreeContour with per-segment inclinations"

    # Verify per-segment inclinations preserved
    inclinations_read = feature_read.contour_param_object.inclination
    assert len(inclinations_read) == 4
    assert tol.is_close(inclinations_read[0], 30.0)
    assert tol.is_close(inclinations_read[1], 45.0)
    assert tol.is_close(inclinations_read[2], 60.0)
    assert tol.is_close(inclinations_read[3], 90.0)


def test_btlx_reader_free_contour_with_dual_contour_roundtrip(tol):
    """Test that FreeContour with DualContour parameters survives roundtrip."""
    model = TimberModel()

    # Create a plate
    plate = Plate(Frame.worldXY(), length=1000, width=500, thickness=20)

    # Create FreeContour with DualContour
    principal = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 100, 0), Point(0, 0, 0)])
    associated = Polyline([Point(10, 10, 10), Point(90, 10, 10), Point(90, 90, 10), Point(10, 90, 10), Point(10, 10, 10)])
    dual_contour = DualContour(principal, associated)
    free_contour = FreeContour(dual_contour)
    plate.add_features(free_contour)
    model.add_element(plate)

    # Roundtrip
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)
    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify
    assert len(reader.errors) == 0
    plate_read = model_read.plates[0]

    # Find the DualContour feature
    feature_read = None
    for f in plate_read.features:
        if isinstance(f, FreeContour) and isinstance(f.contour_param_object, DualContour):
            feature_read = f
            break

    assert feature_read is not None, "Could not find FreeContour with DualContour"
    assert isinstance(feature_read, FreeContour)
    assert isinstance(feature_read.contour_param_object, DualContour)

    # Verify both contours preserved
    dual_read = feature_read.contour_param_object
    assert tol.is_allclose(dual_read.principal_contour.points, principal.points)
    assert tol.is_allclose(dual_read.associated_contour.points, associated.points)


def test_btlx_reader_error_handling_malformed_xml():
    """Test that malformed XML raises appropriate error."""
    reader = BTLxReader()
    malformed_xml = "<?xml version='1.0'?><BTLx>"  # No closing tag

    with pytest.raises(ET.ParseError):
        reader.xml_to_model(malformed_xml)


def test_btlx_reader_error_handling_missing_project():
    """Test that missing Project element raises ValueError."""
    reader = BTLxReader()
    xml_without_project = '<?xml version="1.0"?><BTLx xmlns="https://www.design2machine.com"></BTLx>'

    with pytest.raises(ValueError, match="No Project element found"):
        reader.xml_to_model(xml_without_project)


def test_btlx_reader_error_handling_unsupported_processing():
    """Test that unsupported processing types are logged to errors."""
    reader = BTLxReader()
    xml_with_unknown = """<?xml version="1.0"?>
    <BTLx xmlns="https://www.design2machine.com">
      <Project Name="Test">
        <Parts>
          <Part Length="1000.000" Width="100.000" Height="100.000" OrderNumber="1" ElementNumber="test" Annotation="test">
            <Transformations>
              <Transformation GUID="{12345678-1234-1234-1234-123456789ABC}">
                <Position>
                  <ReferencePoint X="0" Y="0" Z="0"/>
                  <XVector X="1" Y="0" Z="0"/>
                  <YVector X="0" Y="1" Z="0"/>
                </Position>
              </Transformation>
            </Transformations>
            <Processings>
              <UnknownProcessing>
                <SomeParameter>value</SomeParameter>
              </UnknownProcessing>
            </Processings>
          </Part>
        </Parts>
      </Project>
    </BTLx>"""

    model = reader.xml_to_model(xml_with_unknown)

    # Model should be created successfully (non-fatal error)
    assert isinstance(model, TimberModel)
    assert len(model.beams) == 1

    # But error should be logged
    assert len(reader.errors) == 1
    assert "Unsupported processing type: UnknownProcessing" in reader.errors[0]


def test_btlx_reader_plate_multiple_features_roundtrip(tol):
    """Test plate with both outline FreeContour and aperture features."""
    model = TimberModel()

    # Create a plate with outline contour
    plate_polyline = Polyline([Point(0, 0, 0), Point(1000, 0, 0), Point(1000, 500, 0), Point(0, 500, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(plate_polyline, 20.0)
    plate.name = "plate_with_aperture"

    # Add aperture contour
    aperture_polyline = Polyline([Point(200, 100, 0), Point(800, 100, 0), Point(800, 400, 0), Point(200, 400, 0), Point(200, 100, 0)])
    aperture_contour = Contour(polyline=aperture_polyline, depth=10.0, depth_bounded=True, inclination=[90.0])
    aperture_feature = FreeContour(aperture_contour, counter_sink=True)
    plate.add_features(aperture_feature)

    model.add_element(plate)

    # Roundtrip
    writer = BTLxWriter()
    xml_string = writer.model_to_xml(model)
    reader = BTLxReader()
    model_read = reader.xml_to_model(xml_string)

    # Verify
    assert len(reader.errors) == 0
    assert len(model_read.plates) == 1
    plate_read = model_read.plates[0]

    # Note: Plates auto-generate an outline feature from outline_a/outline_b,
    # and the BTLx includes all features that were written (outline + aperture).
    # So we'll have: auto-generated outline + written outline + written aperture = 3 features
    # We just need to verify the aperture feature is present and correct
    assert len(plate_read.features) >= 2

    # All should be FreeContour instances
    assert all(isinstance(f, FreeContour) for f in plate_read.features)

    # Find the aperture (counter_sink=True)
    aperture_read = None
    for f in plate_read.features:
        if f.counter_sink:
            aperture_read = f
            break

    assert aperture_read is not None, "Could not find aperture with counter_sink=True"
    assert aperture_read.counter_sink is True


def test_btlx_reader_processing_instantiation_error():
    """Test that invalid processing parameters log errors but don't crash."""
    reader = BTLxReader()

    # Create BTLx with JackRafterCut missing required parameter (should fail instantiation)
    xml_with_bad_processing = """<?xml version="1.0"?>
    <BTLx xmlns="https://www.design2machine.com">
      <Project Name="Test">
        <Parts>
          <Part Length="1000.000" Width="100.000" Height="100.000" OrderNumber="1" ElementNumber="test" Annotation="test">
            <Transformations>
              <Transformation GUID="{12345678-1234-1234-1234-123456789ABC}">
                <Position>
                  <ReferencePoint X="0" Y="0" Z="0"/>
                  <XVector X="1" Y="0" Z="0"/>
                  <YVector X="0" Y="1" Z="0"/>
                </Position>
              </Transformation>
            </Transformations>
            <Processings>
              <JackRafterCut Orientation="start" ReferencePlaneID="1">
                <StartX>10.000</StartX>
                <StartY>20.000</StartY>
                <!-- Missing required parameters like Angle, Inclination -->
              </JackRafterCut>
            </Processings>
          </Part>
        </Parts>
      </Project>
    </BTLx>"""

    model = reader.xml_to_model(xml_with_bad_processing)

    # Model should still be created (non-fatal error)
    assert isinstance(model, TimberModel)
    assert len(model.beams) == 1

    # But error should be logged
    assert len(reader.errors) > 0
    # Check that error message mentions the processing type
    error_messages = " ".join(reader.errors)
    assert "JackRafterCut" in error_messages or "Failed to instantiate" in error_messages
