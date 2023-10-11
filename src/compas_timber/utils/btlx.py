import uuid
import xml.etree.ElementTree as ET
import numpy as np
import xml.dom.minidom
from compas_timber.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas.geometry import Frame
from compas.geometry import Brep
from compas.geometry import Plane
from compas.geometry import Vector
from compas.datastructures import GeometricFeature
from compas.datastructures import ParametricFeature
from compas.datastructures import Part
import compas.data

# import compas_occ


class BTLx:
    def __init__(self, assembly, shape_data=None):
        self.assembly = assembly

        self.file_attributes = {
            "xmlns": "https://www.design2machine.com",
            "Version": "2.0.0",
            "Language": "en",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd",
        }
        self.string = ET.Element("BTLx", self.file_attributes)
        self.string.append(self.file_history())
        self.project = ET.SubElement(self.string, "Project", Name="testProject")
        self.parts = ET.SubElement(self.project, "Parts")
        self.btlx_ET = ET.ElementTree(self.string)
        self.msg = ""

        i = 0
        for beam in assembly.beams:
            for feature in beam.features:
                self.msg += repr(feature)
            self.parts.append(self.BTLx_Part(beam, i, shape_data).part)
            i += 1

    def __str__(self):
        return xml.dom.minidom.parseString(ET.tostring(self.string)).toprettyxml(indent="   ")

    def file_history(self):
        file_history = ET.Element("FileHistory")
        initial_export_program = ET.SubElement(
            file_history,
            "InitialExportProgram",
            CompanyName="Gramazio Kohler Research",
            ProgramName="COMPAS_Timber",
            ProgramVersion="1.7",
            ComputerName="PC",
            UserName="OB",
            FileName="tenon-mortise.BTLX",
            Date="2021-12-02",
            Time="14:08:00",
            Comment="",
        )
        return file_history

    class BTLx_Part:
        def __init__(self, beam, index, shape_data=None):
            btlx_corner_reference_point = (
                beam.frame.point
                - (beam.frame.yaxis * beam.width)
                - np.cross(beam.frame.xaxis, beam.frame.yaxis) * beam.height
            )
            self.part = ET.Element(
                "Part",
                SingleMemberNumber="",
                AssemblyNumber="",
                OrderNumber="",
                Designation="",
                Annotation="",
                Storey="",
                Group="",
                Package="",
                Material="",
                TimberGrade="",
                QualityGrade="",
                Count="1",
                Length="",
                Height="",
                Width="",
                PlaningLength="0",
                Weight="0",
                ProcessingQuality="automatic",
                StoreyType="",
                ElementNumber="00",
                Layer="0",
                ModuleNumber="",
            )
            self.part.set("SingleMemberNumber", str(index))
            self.part.set("OrderNumber", str(index))
            self.part.set("Length", str(beam.length))
            self.part.set("Width", str(beam.width))
            self.part.set("Height", str(beam.height))

            transformations = ET.SubElement(self.part, "Transformations")
            guid = "{" + str(uuid.uuid4()) + "}"
            transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
            position = ET.SubElement(transformation, "Position")

            reference_point = ET.SubElement(position, "ReferencePoint", X="", Y="", Z="")
            reference_point.set("X", str(btlx_corner_reference_point.x))
            reference_point.set("Y", str(btlx_corner_reference_point.y))
            reference_point.set("Z", str(btlx_corner_reference_point.z))

            x_vector = ET.SubElement(position, "XVector", X="", Y="", Z="")
            x_vector.set("X", str(beam.frame.xaxis.x))
            x_vector.set("Y", str(beam.frame.xaxis.y))
            x_vector.set("Z", str(beam.frame.xaxis.z))

            y_vector = ET.SubElement(position, "YVector", X="", Y="", Z="")
            y_vector.set("X", str(beam.frame.yaxis.x))
            y_vector.set("Y", str(beam.frame.yaxis.y))
            y_vector.set("Z", str(beam.frame.yaxis.z))

            grain_direction = ET.SubElement(self.part, "GrainDirection", X="1", Y="0", Z="0", Align="no")
            reference_side = ET.SubElement(self.part, "ReferenceSide", Side="3", Align="no")
            processings = ET.SubElement(self.part, "Processings")

            a = 0
            for feature in beam.features:
                processings.append(self.add_process(a))
                a += 1

            shape = ET.SubElement(self.part, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coordIndex="")
            indexed_face_set.set("coordIndex", '"' + shape_data[0][index] + '"')
            coordinate = ET.SubElement(indexed_face_set, "Coordinate", point='"' + shape_data[1][index] + '"')

        def add_process(self, feature):
            if feature == 0:
                process = ET.Element(
                    "JackRafterCut", Name="Jack cut", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2"
                )
                orientation = ET.SubElement(process, "Orientation")
                orientation.text = "end"
                start_x = ET.SubElement(process, "StartX")
                start_x.text = "1402.659"
                start_y = ET.SubElement(process, "StartY")
                start_y.text = "0"
                start_depth = ET.SubElement(process, "StartDepth")
                start_depth.text = "0"
                angle = ET.SubElement(process, "Angle")
                angle.text = "55"
                inclination = ET.SubElement(process, "Inclination")
                inclination.text = "90"
            elif feature == 1:
                process = ET.Element(
                    "Mortise", Name="Mortise", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2"
                )
            else:
                process = ET.Element(
                    "Tenon", Name="Tenon", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2"
                )

            return process


def get_btlx_string(assembly_json, shape_data=None):
    assembly = compas.json_loads(assembly_json)
    print("Hello, beams")
    btlx_ins = BTLx(assembly, shape_data)
    return [str(btlx_ins), btlx_ins.msg]
    # return ["Hello, beams"]
