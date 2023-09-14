import uuid
import xml.etree.ElementTree as ET
import numpy as np
import xml.dom.minidom
from compas_timber.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Vector
import compas.data


class BTLx:
    def __init__(self, assembly):
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

        print("before adding parts")

        i = 0;
        for beam in range(0,4):
            frame = Frame((0, 0, 0), (0, 0, 1), (0, 1, 0))
            beam = Beam(frame, 2450, 85, 150, "mesh")
            self.parts.append(self.BTLx_Part(beam, i).part)
            i+=1

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
        def __init__(self, beam, index):
            frame = Frame((0, 0, 0), (0, 0, 1), (0, 1, 0))
            beam = Beam(frame, 2450, 85, 150, "mesh")

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

            for a in range(3):
                processings.append(self.add_process(a))

            shape = ET.SubElement(self.part, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coorIndex="0")
            coordinate = ET.SubElement(indexed_face_set, "Coordinate", point="0,0,0")

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

def get_btlx_string(assembly_json):
    assembly = compas.json_loads(assembly_json)
    print(assembly.Beams)
    btlx_ins = BTLx(assembly)
    return str(btlx_ins)


def btlx_part_strings(brep):
    brep_vertices = brep.Vertices
    brep_vertices_string = ""
    for vertex in brep_vertices:
        brep_vertices_string += str(vertex.Location.X) + " " + str(vertex.Location.Y) + " " + str(vertex.Location.Z) + " "
    brep_indices = []
    for face in brep.Faces:
        face_indices = []
        for edge_index in face.AdjacentEdges():
            edge = brep.Edges[edge_index]
            start_vertex = edge.StartVertex
            end_vertex = edge.EndVertex
            face_indices.append(start_vertex.VertexIndex)
            face_indices.append(end_vertex.VertexIndex)
        face_indices = list(set(face_indices))
        for index in ccw_sorted_vertex_indices(face_indices, brep, face):
            brep_indices.append(index)
        brep_indices.append(-1)
    brep_indices.pop(-1)
    brep_indices_string = ""
    for index in brep_indices:
        brep_indices_string += str(index) + " "
    return [brep_vertices_string, brep_indices_string]


def angle(frame, point):
    point_vector = Vector(point[0] - frame.point[0], point[1] - frame.point[1], point[2] - frame.point[2])
    return Vector.angle_vectors_signed(frame.xaxis, point_vector, frame.normal)

def ccw_sorted_vertex_indices(indices, brep, brep_face):
    frame_origin = brep_face.PointAt(0.5, 0.5)
    frame_normal = brep_face.NormalAt(0.5, 0.5)
    normal_frame = Frame.from_plane(Plane(frame_origin, frame_normal))
    sorted_indices = sorted(indices, key=lambda index: angle(normal_frame, brep.Vertices[index].Location))
    return sorted_indices


