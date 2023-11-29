import os
import uuid
from datetime import date
from datetime import datetime
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import compas

from collections import OrderedDict
from compas.geometry import Frame
from compas.geometry import Transformation


class BTLx(object):
    POINT_PRECISION = 3
    ANGLE_PRECISION = 3
    REGISTERED_JOINTS = {}
    FILE_ATTRIBUTES = OrderedDict(
        [
            ("xmlns", "https://www.design2machine.com"),
            ("Version", "2.0.0"),
            ("Language", "en"),
            ("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"),
            (
                "xsi:schemaLocation",
                "https://www.design2machine.com https://www.design2machine.com/btlx/btlx_2_0_0.xsd",
            ),
        ]
    )

    def __init__(self, assembly):
        self.assembly = assembly
        self.parts = {}
        self._test = []
        self.joints = assembly.joints
        self.process_assembly()

    @property
    def history(self):
        return {
            "CompanyName": "Gramazio Kohler Research",
            "ProgramName": "COMPAS_Timber",
            "ProgramVersion": "Compas: {}".format(compas.__version__),
            "ComputerName": "{}".format(os.getenv("computername")),
            "UserName": "{}".format(os.getenv("USERNAME")),
            "FileName": "",
            "Date": "{}".format(date.today()),
            "Time": "{}".format(datetime.now().strftime("%H:%M:%S")),
            "Comment": "",
        }

    def btlx_string(self):
        """returns a pretty xml sting for visualization in GH, Terminal, etc"""
        self.ET_element = ET.Element("BTLx", BTLx.FILE_ATTRIBUTES)
        self.ET_element.append(self.file_history)
        self.project_element = ET.SubElement(self.ET_element, "Project", Name="testProject")
        self.parts_element = ET.SubElement(self.project_element, "Parts")

        for part in self.parts.values():
            self.parts_element.append(part.et_element)
        return MD.parseString(ET.tostring(self.ET_element)).toprettyxml(indent="   ")

    def process_assembly(self):
        for beam in self.assembly.beams:
            self.parts[str(beam.key)] = BTLxPart(beam)
        for joint in self.joints:
            factory_type = self.REGISTERED_JOINTS.get(str(type(joint)))
            factory_type.apply_processings(joint, self.parts)

    @classmethod
    def register_joint(cls, joint_type, process_type):
        cls.REGISTERED_JOINTS[str(joint_type)] = process_type

    @property
    def file_history(self):
        file_history = ET.Element("FileHistory")
        file_history.append(ET.Element("InitialExportProgram", self.history))
        return file_history


class BTLxPart(object):
    def __init__(self, beam):
        self.beam = beam
        self.key = beam.key
        self.length = beam.length
        self.width = beam.width
        self.height = beam.height
        self.frame = Frame(
            self.beam.long_edges[2].closest_point(self.beam.blank_frame.point),
            beam.frame.xaxis,
            beam.frame.yaxis,
        )  # I used long_edge[2] because it is in Y and Z negative. Using that as reference puts the beam entirely in positive coordinates.
        self._test = []
        self.blank_length = beam.blank_length
        self.key = beam.key
        self._reference_surfaces = []
        self.processings = []
        self._et_element = None

    def reference_surface_planes(self, index):  # TODO: fix Beam.shape definition and update this.
        if len(self._reference_surfaces) != 6:
            self._reference_surfaces = {
                "1": Frame(self.frame.point, self.frame.xaxis, self.frame.zaxis),
                "2": Frame(
                    self.frame.point + self.frame.yaxis * self.width,
                    self.frame.xaxis,
                    -self.frame.yaxis,
                ),
                "3": Frame(
                    self.frame.point + self.frame.yaxis * self.width + self.frame.zaxis * self.height,
                    self.frame.xaxis,
                    -self.frame.zaxis,
                ),
                "4": Frame(
                    self.frame.point + self.frame.zaxis * self.height,
                    self.frame.xaxis,
                    self.frame.yaxis,
                ),
                "5": Frame(self.frame.point, self.frame.zaxis, self.frame.yaxis),
                "6": Frame(
                    self.frame.point + self.frame.xaxis * self.blank_length + self.frame.yaxis * self.width,
                    self.frame.zaxis,
                    -self.frame.yaxis,
                ),
            }
        return self._reference_surfaces[str(index)]

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
            "Length": "{:.{prec}f}".format(self.blank_length, prec=BTLx.POINT_PRECISION),
            "Height": "{:.{prec}f}".format(self.height, prec=BTLx.POINT_PRECISION),
            "Width": "{:.{prec}f}".format(self.width, prec=BTLx.POINT_PRECISION),
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
        for process in self.processings:
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
            processings_et = ET.Element("Processings")
            for process in self.processings:
                processings_et.append(process.et_element)
            self._et_element.append(processings_et)
            self._et_element.append(self.et_shape)
        return self._et_element

    @property
    def et_transformations(self):
        transformations = ET.Element("Transformations")
        guid = "{" + str(uuid.uuid4()) + "}"
        transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
        position = ET.SubElement(transformation, "Position")
        position.append(ET.Element("ReferencePoint", self.et_point_vals(self.frame.point)))
        position.append(ET.Element("XVector", self.et_point_vals(self.frame.xaxis)))
        position.append(ET.Element("YVector", self.et_point_vals(self.frame.yaxis)))
        return transformations

    @property
    def et_shape(self):
        shape = ET.Element("Shape")
        indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coordIndex="")
        indexed_face_set.set("coordIndex", " ")
        indexed_face_set.append(ET.Element("Coordinate"))
        # indexed_face_set.set("coordIndex", self.shape_strings[0])
        # indexed_face_set.append(ET.Element("Coordinate", point=self.shape_strings[1]))
        return shape

    @property
    def shape_strings(self):
        if not self._shape_strings:
            brep_vertex_points = []
            brep_indices = []
            try:
                for face in self.beam.geometry.faces:
                    for loop in face.loops:
                        for vertex in loop.vertices:
                            if brep_vertex_points.contains(vertex.point):
                                brep_indices.append(brep_vertex_points.index(vertex.point))
                            else:
                                brep_vertex_points.append(vertex.point)
                                brep_indices.append(len(brep_vertex_points))

                brep_indices.append(-1)
                brep_indices.pop(-1)
            except NotImplementedError:
                print("brep.face.loop.vertices not implemented")
            brep_indices_string = " "
            for index in brep_indices:
                brep_indices_string += str(index) + " "

            brep_vertices_string = " "
            for point in brep_vertex_points:
                xform = Transformation.from_frame_to_frame(self.frame, Frame((0, 0, 0), (1, 0, 0), (0, 1, 0)))
                point.transform(xform)
                brep_vertices_string += "{:.{prec}f} {:.{prec}f} {:.{prec}f} ".format(
                    point.x, point.y, point.z, prec=BTLx.POINT_PRECISION
                )
            self._shape_strings = [brep_indices_string, brep_vertices_string]
        return self._shape_strings


class BTLxProcess(object):

    """
    Generic class for BTLx processings.
    This should be instantiated and appended to BTLxPart.processings in a specific btlx_process class (eg BTLxJackCut)
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
            child.text = value
            element.append(child)
        return element
