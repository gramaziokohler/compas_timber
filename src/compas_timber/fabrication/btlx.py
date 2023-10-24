import os
import uuid
import sys
from datetime import date
from datetime import datetime


import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import compas

if not compas.IPY:
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
        from compas.files._xml import xml_cpython as xml_impl
    else:
        from compas.files._xml import xml_pre_38 as xml_impl
else:
    from compas.files._xml import xml_cli as xml_impl


import math
from collections import defaultdict
from collections import OrderedDict

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
        self.joints = []
        self.parts = {}
        self._test = []
        self.btlx_joints = []
        self._blanks = None
        self.history =  {
                "CompanyName":"Gramazio Kohler Research",
                "ProgramName":"COMPAS_Timber",
                "ProgramVersion":"Compas: {}".format(compas.__version__),
                "ComputerName":"{}".format(os.getenv("computername")),
                "UserName":"{}".format(os.getenv("USERNAME")),
                "FileName":"",
                "Date":"{}".format(date.today()),
                "Time":"{}".format(datetime.now().strftime("%H:%M:%S")),
                "Comment":"",
                }
        self.process_assembly()
        self.process_joints()


    def __str__(self):
        """returns a pretty xml sting for visualization in GH, Terminal, etc"""
        self.ET_element = ET.Element("BTLx", self.file_attributes)
        self.ET_element.append(self.file_history)
        self.project_element = ET.SubElement(self.ET_element, "Project", Name="testProject")
        self.parts_element = ET.SubElement(self.project_element, "Parts")

        for part in self.parts.values():
            self.parts_element.append(part.et_element)

        return MD.parseString(ET.tostring(self.ET_element)).toprettyxml(indent="   ")


    def process_assembly(self):
        for joint in self.assembly.joints:
            btlx_joint = BTLxJoint(joint)
            for beam in btlx_joint.beams:
                if self.parts.keys().__contains__(str(beam.key)):
                    btlx_joint.parts[str(beam.key)] = self.parts[str(beam.key)]
                else:
                    self.parts[str(beam.key)] = BTLxPart(beam)
                    btlx_joint.parts[str(beam.key)] = self.parts[str(beam.key)]
            self.joints.append(btlx_joint)

    def process_joints(self):
        for joint in self.joints:
            joint.process_joint()

    @property
    def blanks(self):
        if not self._edges:
            self._edges = []
            for part in self.parts:
                for tuple in part.blank_geometry.edges:
                    self._edges.append(Line(part.blank_geometry.points[tuple[0]], part.blank_geometry.points[tuple[1]]))
        return self._edges

    @property
    def file_attributes(self):
        return OrderedDict([
        ("xmlns", "https://www.design2machine.com"),
        ("Version", "2.0.0"),
        ("Language", "en"),
        ("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"),
        ("xsi:schemaLocation", "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd")
        ])


    @property
    def file_history(self):
        file_history = ET.Element("FileHistory")
        file_history.append(ET.Element(
                "InitialExportProgram",
                self.history
            )
        )
        return file_history


class BTLxPart(object):
    def __init__(self, beam):
        self.beam = beam
        self.length = beam.length
        self.width = beam.width
        self.height = beam.height
        self.frame = beam.frame
        self._test = []
        self.geometry_type = "brep"
        self.orientation = None
        self.blank_geometry = beam.shape
        self._blank_frame = None
        self.blank_length = beam.length
        self.key = beam.key
        self.start_trim = None
        self.end_trim = None
        self._reference_surfaces = []
        self.processes = []
        self._et_element = None

    @property
    def reference_surfaces(self):  # TODO: fix Beam.shape definition and update this.
        if len(self._reference_surfaces) != 6:
            self._reference_surfaces = {
                "1": Frame(self.blank_frame.point, self.blank_frame.xaxis, self.blank_frame.zaxis),
                "2": Frame(self.blank_frame.point + self.blank_frame.yaxis * self.width, self.blank_frame.xaxis, -self.blank_frame.yaxis),
                "3": Frame(self.blank_frame.point + self.blank_frame.yaxis * self.width + self.blank_frame.zaxis * self.height, self.blank_frame.xaxis, -self.blank_frame.zaxis),
                "4": Frame(self.blank_frame.point + self.blank_frame.zaxis * self.height, self.blank_frame.xaxis, self.blank_frame.yaxis),
                "5": Frame(self.blank_frame.point, self.blank_frame.zaxis, self.blank_frame.yaxis),
                "6": Frame(self.blank_frame.point + self.blank_frame.xaxis * self.blank_length + self.blank_frame.yaxis * self.width, self.blank_frame.zaxis, -self.blank_frame.yaxis)
            }
        return self._reference_surfaces

    @property
    def blank_frame(self):
        blank_frame_point = self.beam.long_edges[2].closest_point(
            self.beam.frame.point
        )  # I used long_edge[2] because it is in Y and Z negative. Using that as reference puts the beam entirely in positive coordinates.
        self._blank_frame = Frame(
            blank_frame_point,
            self.frame.xaxis,
            self.frame.yaxis,
        )
        return self._blank_frame

    @property
    def attr(self):
        return {
            "SingleMemberNumber": str(self.key),
            "AssemblyNumber": "",
            "OrderNumber": str(self.key),
            "Designation": "",
            "Annotation": "",
            "Storey": "",
            "Group": "",
            "Package": "",
            "Material": "",
            "TimberGrade": "",
            "QualityGrade": "",
            "Count": "1",
            "Length": "{:.{prec}f}".format( self.blank_length, prec=BTLx.POINT_PRECISION),
            "Height": "{:.{prec}f}".format( self.height, prec=BTLx.POINT_PRECISION),
            "Width": "{:.{prec}f}".format( self.width, prec=BTLx.POINT_PRECISION),
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

    def et_point_vals(self, point):
        return {
            "X": "{:.{prec}f}".format(point.x, prec=BTLx.POINT_PRECISION),
            "Y": "{:.{prec}f}".format(point.y, prec=BTLx.POINT_PRECISION),
            "Z": "{:.{prec}f}".format(point.z, prec=BTLx.POINT_PRECISION),
        }

    @property
    def et_element(self):
        if not self._et_element:
            self._et_element = ET.Element("Part", self.attr)
            self._shape_strings = None
            self._et_element.append(self.et_transformations)
            self._et_element.append(ET.Element("GrainDirection", X="1", Y="0", Z="0", Align="no"))
            self._et_element.append(ET.Element("ReferenceSide", Side="1", Align="no"))
            processings = ET.Element("Processings")
            for process in self.processes:
                processings.append(process.et_element)
            self._et_element.append(processings)
            self._et_element.append(self.et_shape)
        return self._et_element

    @property
    def et_transformations(self):
        transformations = ET.Element("Transformations")
        guid = "{" + str(uuid.uuid4()) + "}"
        transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
        position = ET.SubElement(transformation, "Position")
        position.append(ET.Element("ReferencePoint", self.et_point_vals(self.blank_frame.point)))
        position.append(ET.Element("XVector", self.et_point_vals(self.blank_frame.xaxis)))
        position.append(ET.Element("YVector", self.et_point_vals(self.blank_frame.yaxis)))
        return transformations

    @property
    def et_shape(self):
        shape = ET.Element("Shape")
        indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coordIndex="")
        indexed_face_set.set("coordIndex", self.shape_strings[0])
        indexed_face_set.append(ET.Element("Coordinate", point=self.shape_strings[1]))
        return shape

    @property
    def shape_strings(self):        #TODO: update for different Brep creation environments
        if not self._shape_strings:
            brep_vertex_points = []
            brep_indices = []
            try:
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
            except:
                    pass
            brep_indices_string = " "
            for index in brep_indices:
                brep_indices_string += str(index) + " "

            brep_vertices_string = " "
            for point in brep_vertex_points:
                xform = Transformation.from_frame_to_frame(self.blank_frame, Frame((0, 0, 0), (1, 0, 0), (0, 1, 0)))
                point.transform(xform)
                brep_vertices_string += "{:.{prec}f} {:.{prec}f} {:.{prec}f} ".format( point.x, point.y, point.z, prec = BTLx.POINT_PRECISION )
            self._shape_strings = [brep_indices_string, brep_vertices_string]
        return self._shape_strings



class BTLxJoint(object):
    REGISTERED_JOINTS = {}

    def __init__(self, joint):
        self.joint = joint
        self.parts = {}
        self._ends = {}

    @property
    def ends(self):
        if len(self._ends) ==0:
            for index, beam in enumerate(self.joint.beams):
                start_distance = min([
                    beam.centerline.start.distance_to_point(self.joint.beams[index - 1].centerline.start),
                    beam.centerline.start.distance_to_point(self.joint.beams[index - 1].centerline.end)
                    ])
                end_distance = min([
                    beam.centerline.end.distance_to_point(self.joint.beams[index - 1].centerline.start),
                    beam.centerline.end.distance_to_point(self.joint.beams[index - 1].centerline.end)
                    ])
                if start_distance < end_distance:
                    self._ends[str(beam.key)] = "start"
                else:
                    self._ends[str(beam.key)] = "end"
        return self._ends


    @property
    def type(self):
        return type(self.joint)

    @property
    def beams(self):
        return self.joint.beams

    def process_joint(self):
        factory_type = BTLxJoint.REGISTERED_JOINTS.get(str(type(self.joint)))
        factory_type.apply_processes(self)

    @classmethod
    def register_joint(cls, joint_type, process_type):
        cls.REGISTERED_JOINTS[str(joint_type)] = process_type



class BTLxProcess(object):

    """
    Generic class for BTLx Processes.
    This should be instantiated and appended to BTLxPart.processes in a specific btlx_process class (eg BTLxJackCut)
    """
    def __init__(self, name, attr, params):
        self.name = name
        self.attr = attr
        self.params = params


    @property
    def et_element(self):
        element = ET.Element(self.name, self.attr)
        for key, value in self.params.items():
            child = ET.Element(key)
            child.text = (value)
            element.append(child)
        return element
