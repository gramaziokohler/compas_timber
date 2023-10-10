import uuid
import xml.etree.ElementTree as ET
import xml.dom.minidom
import compas.data
import math
from collections import defaultdict

from compas.geometry import Frame
from compas.geometry import Box
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import Transformation
from compas.geometry import Translation

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.utils.compas_extra import intersection_line_plane



class BTLx(object):

    POINT_PRECISION = 3
    ANGLE_PRECISION = 3

    def __init__(self, assembly):
        self.assembly = assembly
        self.parts = []
        self._test = []
        self._joints_per_beam = None
        self._msg = []

        for index, beam in enumerate(self.assembly.beams):
            part = BTLxPart(beam, index, self.joints_per_beam[str(beam.key)])
            self.parts.append(part)

    def __str__(self):
        self.ET_element = ET.Element("BTLx", self.file_attributes)
        self.ET_element.append(self.file_history)
        self.project_element = ET.SubElement(self.ET_element, "Project", Name="testProject")
        self.parts_element = ET.SubElement(self.project_element, "Parts")

        i = 0
        for part in self.parts:
            self.parts_element.append(part.et_element)
            i += 1

        return xml.dom.minidom.parseString(ET.tostring(self.ET_element)).toprettyxml(indent="   ")

    @property
    def joints_per_beam(self):
        if self._joints_per_beam == None:
            jpb = defaultdict(list)
            for joint in self.assembly.joints:
                for beam in joint.beams:
                    jpb[str(beam.key)].append(joint)
            self._joints_per_beam = jpb
        return self._joints_per_beam

    @property
    def test(self):
        items = []
        for item in self._test:
            items.append(item)
        for part in self.parts:
            for item in part.test:
                items.append(item)
        return items

    @property
    def msg(self):
        msg_out = ''
        if len(self._msg) > 0:
            for msg in self._msg:
                msg_out += msg
        for index, part in enumerate(self.parts):
            if len(part.msg) > 0:
                msg_out += f'part {index} message:'
                msg_out+=f'{part.msg} \n'
        return msg_out

    @property
    def file_attributes(self):
        return {
            "xmlns": "https://www.design2machine.com",
            "Version": "2.0.0",
            "Language": "en",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd",
        }

    @property
    def file_history(self):
        file_history = ET.Element("FileHistory")
        file_history.append(ET.Element(
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
        ))
        return file_history

class BTLxPart(object):
    def __init__(self, beam, index, joints = None):
        self.beam = beam
        self.joints = joints
        self.length = beam.length
        self.width = beam.width
        self.height = beam.height
        self.frame = beam.frame
        self._msg = []
        self._test = []
        self.geometry_type = "brep"
        self.orientation = None
        self.blank_geometry = beam.shape
        self._blank_frame = None
        self.blank_length = beam.length
        self.index = index
        self.start_trim = None
        self.end_trim = None
        self._reference_surfaces = []
        self.processes = []
        self._et_element = None
        self.generate_processes()

    @property
    def attr(self):
        return{
        "SingleMemberNumber": str(self.index),
        "AssemblyNumber": "",
        "OrderNumber": str(self.index),
        "Designation": "",
        "Annotation": "",
        "Storey": "",
        "Group": "",
        "Package": "",
        "Material": "",
        "TimberGrade": "",
        "QualityGrade": "",
        "Count": "1",
        "Length": f'{self.blank_length:.{BTLx.POINT_PRECISION}f}',
        "Height": f'{self.height:.{BTLx.POINT_PRECISION}f}',
        "Width": f'{self.width:.{BTLx.POINT_PRECISION}f}',
        "PlaningLength": "0",
        "Weight": "0",
        "ProcessingQuality": "automatic",
        "StoreyType": "",
        "ElementNumber": "00",
        "Layer": "0",
        "ModuleNumber": "",
        }

    @property
    def test(self):
        items = []
        for item in self._test:
            items.append(item)
        for process in self.processes:
            for item in process.test:
                items.append(item)
        return items

    @property
    def msg(self):
        msg_out = ''
        if len(self._msg) > 0:
            for msg in self._msg:
                msg_out += msg
            msg_out+=f'\n'

        for index, process in enumerate(self.processes):
            try:
                if len(process.msg) > 0:
                    msg_out += f'process {index} message:'
                    msg_out+=f'{process.msg} \n'
            except:
                pass
        return msg_out

    @property
    def et_element(self):
        if not self._et_element:
            self._et_element = ET.Element("Part", self.attr)
            self._et_element.set("SingleMemberNumber", f'{self.index}')
            self._et_element.set("OrderNumber", f'{self.index}')
            self._et_element.set("Length", f'{self.blank_length:.{BTLx.POINT_PRECISION}f}')
            self._et_element.set("Width", f'{self.width:.{BTLx.POINT_PRECISION}f}')
            self._et_element.set("Height", f'{self.height:.{BTLx.POINT_PRECISION}f}')
            self._shape_strings = None

            transformations = ET.SubElement(self._et_element, "Transformations")
            guid = "{" + str(uuid.uuid4()) + "}"
            transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
            position = ET.SubElement(transformation, "Position")

            reference_point_vals = {
                "X": f'{self.blank_frame.point.x:.{BTLx.POINT_PRECISION}f}',
                "Y": f'{self.blank_frame.point.y:.{BTLx.POINT_PRECISION}f}',
                "Z": f'{self.blank_frame.point.z:.{BTLx.POINT_PRECISION}f}',
                }
            position.append(ET.Element("ReferencePoint", reference_point_vals))

            x_vector_vals = {
                "X": f'{self.blank_frame.xaxis.x:.{BTLx.POINT_PRECISION}f}',
                "Y": f'{self.blank_frame.xaxis.y:.{BTLx.POINT_PRECISION}f}',
                "Z": f'{self.blank_frame.xaxis.z:.{BTLx.POINT_PRECISION}f}',
                }
            position.append(ET.Element("XVector", x_vector_vals))

            y_vector_vals = {
                "X": f'{self.blank_frame.yaxis.x:.{BTLx.POINT_PRECISION}f}',
                "Y": f'{self.blank_frame.yaxis.y:.{BTLx.POINT_PRECISION}f}',
                "Z": f'{self.blank_frame.yaxis.z:.{BTLx.POINT_PRECISION}f}',
                }
            position.append(ET.Element("YVector", y_vector_vals))

            self._et_element.append(ET.Element("GrainDirection", X="1", Y="0", Z="0", Align="no"))
            self._et_element.append(ET.Element("ReferenceSide", Side="3", Align="no"))
            processings = ET.SubElement(self._et_element, "Processings")

            for process in self.processes:
                processings.append(process.et_element)

            shape = ET.SubElement(self._et_element, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coordIndex="")
            strings = self.shape_strings
            indexed_face_set.set("coordIndex", strings[0])
            indexed_face_set.append(ET.Element("Coordinate", point=strings[1]))
        return self._et_element

    @property
    def reference_surfaces(self): #TODO: fix Beam.shape definition and update this.
        if len(self._reference_surfaces) != 6:
            self._reference_surfaces = []
            self._reference_surfaces.append(Frame(self.blank_frame.point, self.blank_frame.xaxis, self.blank_frame.zaxis))
            point = self.blank_frame.point + self.blank_frame.yaxis * self.width
            self._reference_surfaces.append(Frame(point, self.blank_frame.xaxis, -self.blank_frame.yaxis))
            point = (
                self.blank_frame.point + self.blank_frame.yaxis * self.width + self.blank_frame.zaxis * self.height
            )
            self._reference_surfaces.append(Frame(point, self.blank_frame.xaxis, -self.blank_frame.zaxis))
            point = self.blank_frame.point + self.blank_frame.zaxis * self.height
            self._reference_surfaces.append(Frame(point, self.blank_frame.xaxis, self.blank_frame.yaxis))
            self._reference_surfaces.append(Frame(self.blank_frame.point, self.blank_frame.zaxis, self.blank_frame.yaxis))
            point = (
                self.blank_frame.point
                + self.blank_frame.xaxis * self.blank_length
                + self.blank_frame.yaxis * self.width
            )
            self._reference_surfaces.append(Frame(point, self.blank_frame.zaxis, -self.blank_frame.yaxis))
        return self._reference_surfaces

    @property
    def shape_strings(self):
        if not self._shape_strings:
            brep_vertex_points = []
            brep_indices = []

            for face in self.beam.geometry.faces:
                for loop in face.loops:
                    for vertex in loop.vertices:
                        try:
                            vertex_index = brep_vertex_points.index(vertex.point)
                            brep_indices.append(vertex_index)
                        except:
                            brep_vertex_points.append(vertex.point)
                            brep_indices.append(len(brep_vertex_points))
                brep_indices.append(-1)
            brep_indices.pop(-1)

            brep_indices_string = " "
            for index in brep_indices:
                brep_indices_string += str(index) + " "

            brep_vertices_string = " "
            for point in brep_vertex_points:
                xform = Transformation.from_frame_to_frame(self.blank_frame, Frame((0,0,0), (1,0,0),(0,1,0)))
                point.transform(xform)
                brep_vertices_string += f'{point.x:.{2}f} {point.y:.{2}f} {point.z:.{2}f} '
            self._shape_strings = [brep_indices_string, brep_vertices_string]
        return self._shape_strings

    @property
    def blank_frame(self):
        blank_frame_point = self.beam.long_edges[2].closest_point(self.beam.frame.point)# I used long_edge[2] because it is in Y and Z negative. Using that as reference puts the beam entirely in positive coordinates.
        self._blank_frame = Frame(
            blank_frame_point,
            self.frame.xaxis,
            self.frame.yaxis,
        )
        return self._blank_frame


    def generate_processes(self):
        for joint in self.joints:
            process = BTLxProcess.create(joint, self)
            if process.apply_process:     # If no process is returned then dont append process. Some joints dont require a process for every member, e.g. TButtJoint doesn't change cross beam
                self.processes.append(process)


class BTLxProcess(object):
    registered_processes = {}

    """
    Generic class for BTLx Processes.
    This should not be called or instantiated directly, but rather specific process subclasses should be instantiated using the classmethod BTLxProcess.create()
    """
    def __init__(self):
        self.joint = None
        self.part = None
        self._test = []
        self._msg = []

    @property
    def test(self):
        return self._test

    @property
    def msg(self):
        msg_out = []
        if len(self._msg) > 0:
            for msg in self._msg:
                msg_out.append(msg)
        return msg_out

    @property
    def et_element(self):
        process_et = ET.Element(self.process_type, self.header_attributes)
        for key, val in self.process_params.items():
            child = ET.SubElement(process_et, key)
            child.text = val
        return process_et

    @classmethod
    def create(cls, joint, part):
        process = None
        process_type = BTLxProcess.registered_processes.get(type(joint))
        try:
            process = process_type(joint, part)
        except:
            part._msg.append(f'joint type {type(joint)} not implemented')
        return process

    @classmethod
    def register_process(cls, joint_type, process_type):
        cls.registered_processes[joint_type] = process_type



def get_btlx_string(assembly_json):
    """
    the following method is used to get the btlx string in grasshopper
    """
    assembly = compas.json_loads(assembly_json)
    btlx_ins = BTLx(assembly)
    edges = []
    for part in btlx_ins.parts:
        for tuple in part.blank_geometry.edges:
            edges.append(Line(part.blank_geometry.points[tuple[0]], part.blank_geometry.points[tuple[1]]))
    return [str(btlx_ins), edges, btlx_ins.msg]
