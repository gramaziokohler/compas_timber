# from compas_timber.fabrication import BTLx
import xml.etree.ElementTree as ET
import xml.dom.minidom as dom


def get_btlx_string(assembly_json):
    """
    the following method is used to get the btlx string in grasshopper
    """


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
