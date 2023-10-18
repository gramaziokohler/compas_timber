# from compas_timber.fabrication import BTLx
from compas.geometry import Line
import compas.data

import sys
import xml.etree.ElementTree as ET
import xml.dom.minidom as dom

import compas

if not compas.IPY:
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
        from compas.files._xml import xml_cpython as xml_impl
    else:
        from compas.files._xml import xml_pre_38 as xml_impl
else:
    from compas.files._xml import xml_cli as xml_impl


def get_btlx_string(assembly_json):
    """
    the following method is used to get the btlx string in grasshopper
    """
    # assembly = compas.json_loads(assembly_json)
    # btlx_ins = BTLx(assembly)
    # edges = []
    # for part in btlx_ins.parts:
    #     for tuple in part.blank_geometry.edges:
    #         edges.append(Line(part.blank_geometry.points[tuple[0]], part.blank_geometry.points[tuple[1]]))
    # return [str(btlx_ins), edges, btlx_ins.msg]


def test_xml():
    file_attributes = {
        "xmlns": "https://www.design2machine.com",
        "Version": "2.0.0",
        "Language": "en",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd",
    }
    ET_element = ET.Element("BTLx", file_attributes)
    ET_element.append(ET.Element("poop", shit="shittyshit", otherShit="shittiershit"))
    return dom.parseString(ET.tostring(ET_element)).toprettyxml(indent="   ")
