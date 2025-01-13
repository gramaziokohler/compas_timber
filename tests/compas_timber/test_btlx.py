import os
import pytest

from compas.data import json_load
from compas.tolerance import Tolerance
from compas.geometry import Frame

import xml.etree.ElementTree as ET

import compas
import compas_timber
from compas_timber.fabrication import BTLxWriter
from compas_timber.elements import Beam
from compas_timber.elements import CutFeature
from compas_timber.model import TimberModel


@pytest.fixture(scope="module")
def test_model():
    model_path = os.path.join(compas_timber.DATA, "model_test.json")
    model = json_load(model_path)
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
    assert len(part_elements) == len(list(test_model.beams))

    # Validate each Part element
    for part, beam in zip(part_elements, test_model.beams):
        assert part.get("Length") == "{:.3f}".format(beam.blank_length)
        assert part.get("Height") == "{:.3f}".format(beam.height)
        assert part.get("Width") == "{:.3f}".format(beam.width)


def test_btlx_processings(resulting_btlx, test_model, namespaces):
    # Find the Project element
    project = resulting_btlx.find("d2m:Project", namespaces)
    assert project is not None

    # Find the Parts element within the Project element
    parts = project.find("d2m:Parts", namespaces)
    assert parts is not None

    # Find all Part elements within the Parts element
    part_elements = parts.findall("d2m:Part", namespaces)
    assert len(part_elements) == len(list(test_model.beams))

    # Validate the features and processings
    for part, beam in zip(part_elements, test_model.beams):
        beam_features = beam.features
        processings = part.find("d2m:Processings", namespaces)
        assert len(processings) == len(beam_features)


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
        assert resulting_part.tag == expected_part.tag

        # Validate the Processings element within each Part element
        resulting_processings = resulting_part.find("d2m:Processings", namespaces)
        expected_processings = expected_part.find("d2m:Processings", namespaces)
        assert resulting_processings is not None
        assert expected_processings is not None
        assert resulting_processings.tag == expected_processings.tag

        # Validate all Processing elements within the Processings element
        resulting_processing_elements = resulting_processings.findall("d2m:Processing", namespaces)
        expected_processing_elements = expected_processings.findall("d2m:Processing", namespaces)
        assert len(resulting_processing_elements) == len(expected_processing_elements)

        for resulting_processing, expected_processing in zip(resulting_processing_elements, expected_processing_elements):
            assert resulting_processing.tag == expected_processing.tag
            assert resulting_processing.attrib == expected_processing.attrib


def test_btlx_should_skip_feature():
    writer = BTLxWriter()
    model = TimberModel()
    beam = Beam(Frame.worldXY(), 1000, 100, 100)
    beam.add_features(CutFeature(Frame.worldXY()))
    model.add_element(beam)

    with pytest.warns():
        result = writer.model_to_xml(model)

    assert result is not None
