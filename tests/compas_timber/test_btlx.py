import os
import pytest

from compas.data import json_load
from compas.tolerance import Tolerance
from lxml.etree import ElementTree
from lxml.etree import XML
from lxml.etree import XMLSchema
from lxml.etree import XMLParser
from lxml.etree import fromstring
from lxml.etree import parse

import compas_timber
from compas_timber.fabrication import BTLx

XML_PARSER = XMLParser(remove_blank_text=True)


@pytest.fixture(scope="module")
def test_model():
    model_path = os.path.join(compas_timber.DATA, "model_test.json")
    return json_load(model_path)


@pytest.fixture(scope="module")
def expected_btlx():
    btlx_path = os.path.join(compas_timber.DATA, "model_test.btlx")
    return parse(btlx_path, XML_PARSER)


# TODO: this is currently not working
# @pytest.fixture(scope="module")
# def btlx_schema():
#     schema_path = os.path.join(compas_timber.DATA, "BTLx_2_0_0.xsd")
#     schema_root = None
#     with open(schema_path, "r", encoding="utf-8") as schema:
#         schema_root = parse(schema.read(), XML_PARSER)
#     return XMLSchema(schema_root)


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_btlx(test_model, expected_btlx):
    test_model.process_joinery()

    test_beams = list(test_model.beams)

    btlx_writer = BTLx(test_model)
    btlx_writer.process_model()

    resulting_btlx = fromstring(btlx_writer.btlx_string(), XML_PARSER)

    # TODO: validate the resulting btlx
    # assert btlx_schema.validate(resulting_btlx)
    namespaces = {"d2m": "https://www.design2machine.com"}

    assert resulting_btlx.find(".", namespaces).tag == "{}BTLx".format("{" + namespaces["d2m"] + "}")
    project = resulting_btlx.find("d2m:Project", namespaces)
    assert project is not None

    parts = project.find("d2m:Parts", namespaces)
    assert parts is not None

    parts = parts.findall("d2m:Part", namespaces)
    assert len(parts) == len(test_beams)

    # TODO: compare the features and processings
    # for part, beam in zip(parts, test_model.beams):
    #     beam_features = beam.features
    #     processing = part.findall("d2m:Processings", namespaces)
