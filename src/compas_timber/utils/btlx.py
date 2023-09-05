import uuid
from compas_timber.parts import Beam

from compas_timber.assembly import TimberAssembly
from compas.geometry import Frame
import xml.etree.ElementTree as ET
import numpy as np
import xml.dom.minidom


class BTLx:
    def __init__(self, assembly):

        print("BTLx init")

        self.file_attributes = {
            "xmlns": "https://www.design2machine.com",
            "Version": "2.0.0",
            "Language": "en",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd",
        }
        self.btlx = ET.Element("BTLx", self.file_attributes)
        self.btlx.append(self.file_history())
        self.project = ET.SubElement(self.btlx, "Project")
        self.parts = ET.SubElement(self.project, "Parts")
        self.btlx_ET = ET.ElementTree(self.btlx)

        print("before adding parts")

        for i in range(4):
            frame = Frame((0, 0, 0), (0, 0, 1), (0, 1, 0))
            beam = Beam(frame, 2450, 85, 150, "mesh")
            self.parts.append(self.Part(beam, i).part)

    def __str__(self) -> str:
        return ET.tostring(self.btlx)

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

    class Part:
        def __init__(self, beam, index):
            frame = Frame((0, 0, 0), (0, 0, 1), (0, 1, 0))
            beam = Beam(frame, 2450, 85, 150, "mesh")

            btlx_corner_reference_point = (
                beam.frame.point - (beam.frame.yaxis * beam.width) - np.cross(beam.frame.xaxis, beam.frame.yaxis) * beam.height
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
            self.part.set("Length", str(beam.length))
            self.part.set("Width", str(beam.width))
            self.part.set("Height", str(beam.height))

            transformations = ET.SubElement(self.part, "Transformations")
            guid = str(uuid.uuid4())
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

            for a in range(3):
                processings.append(self.add_process(a))

            shape = ET.SubElement(self.part, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="", coorIndex="")
            coordinate = ET.SubElement(indexed_face_set, "Coordinate", point="")

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


def get_btlx_string(assembly):
    btlx = BTLx(assembly)

    return xml.dom.minidom.parseString(ET.tostring(btlx.btlx)).toprettyxml(indent="   ")



def write_btlx(assembly, path):
    btlx = BTLx(assembly)
    btlx.btlx_ET.write(path)
    msg = xml.dom.minidom.parseString(ET.tostring(btlx.btlx)).toprettyxml(indent="   ")
    with open(path, "w") as f:
        f.write(msg)

    return msg
