import uuid
import xml.etree.ElementTree as ET
import xml.dom.minidom
import compas.data
import math

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
from compas_timber.utils.compas_extra import intersection_line_plane
from compas_timber.parts.features import BeamTrimmingFeature
from compas_timber.parts.features import BeamExtensionFeature


class BTLx:
    def __init__(self, assembly):
        self.assembly = assembly
        self.parts = []
        self._test = []
        self._msg = []

        for beam in self.assembly.beams:
            part = BTLxPart(beam, self)
            self.parts.append(part)
            self._test.append(part.blank_geometry)


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
    def test(self):
        items = []
        for item in self._test:
            items.append(item)
        #self._msg.append(f'part count = {len(self.parts)}')
        for part in self.parts:
            for item in part.test:
                items.append(item)
        return items

    @property
    def msg(self):
        msg_out = []
        if len(self._msg) > 0:
            for msg in self._msg:
                msg_out.append(msg)
        for part in self.parts:
            if len(part.msg) > 0:
                msg_out.append(part.msg)
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


class BTLxPart:
    def __init__(self, beam, parent):
        self.beam = beam
        self.features = beam.features
        self.length = beam.length
        self.width = beam.width
        self.height = beam.height
        self.frame = beam.frame
        self._msg = []
        self._test = []
        self.geometry_type = "brep"
        self.orientation = None
        self.blank_geometry = None
        self.blank_frame = None
        self.blank_length = None
        self._index = len(parent.parts)
        self.start_trim = None
        self.end_trim = None
        self.processes = []
        self._et_element = None
        self.attr = {
            "SingleMemberNumber": "",
            "AssemblyNumber": "",
            "OrderNumber": "",
            "Designation": "",
            "Annotation": "",
            "Storey": "",
            "Group": "",
            "Package": "",
            "Material": "",
            "TimberGrade": "",
            "QualityGrade": "",
            "Count": "1",
            "Length": "",
            "Height": "",
            "Width": "",
            "PlaningLength": "0",
            "Weight": "0",
            "ProcessingQuality": "automatic",
            "StoreyType": "",
            "ElementNumber": "00",
            "Layer": "0",
            "ModuleNumber": "",
        }
        # self._msg.append(f'_trim_processes count = {len(self.trim_processes)}')
        self.generate_blank_geometry()
        self.generate_processes()


    @property
    def test(self):
        items = []
        #self._msg.append(f'_test items count = {len(self._test)}')
        for item in self._test:
            items.append(item)
        for process in self.processes:
            for item in process.test:
                items.append(item)
        return items

    @property
    def msg(self):
        msg_out = []
        for msg in self._msg:
            if len(self._msg) > 0:
                msg_out.append(msg)
        for process in self.processes:
            if len(process.msg) > 0:
                msg_out.append(process.msg)
        return msg_out

    @property
    def et_element(self):
        if not self._et_element:
            point_precision = 3
            self._et_element = ET.Element("Part", self.attr)
            self._et_element.set("SingleMemberNumber", f'{self._index}')
            self._et_element.set("OrderNumber", f'{self._index}')
            self._et_element.set("Length", f'{self.blank_length:.{point_precision}f}')
            self._et_element.set("Width", f'{self.width:.{point_precision}f}')
            self._et_element.set("Height", f'{self.height:.{point_precision}f}')
            self._shape_strings = None

            transformations = ET.SubElement(self._et_element, "Transformations")
            guid = "{" + str(uuid.uuid4()) + "}"
            transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
            position = ET.SubElement(transformation, "Position")

            reference_point_vals = {
                "X": f'{self.blank_frame.point.x:.{point_precision}f}',
                "Y": f'{self.blank_frame.point.y:.{point_precision}f}',
                "Z": f'{self.blank_frame.point.z:.{point_precision}f}',
                }
            reference_point = ET.SubElement(position, "ReferencePoint", reference_point_vals)

            x_vector_vals = {
                "X": f'{self.blank_frame.xaxis.x:.{point_precision}f}',
                "Y": f'{self.blank_frame.xaxis.y:.{point_precision}f}',
                "Z": f'{self.blank_frame.xaxis.z:.{point_precision}f}',
                }
            x_vector = ET.SubElement(position, "XVector", x_vector_vals)

            y_vector_vals = {
                "X": f'{self.blank_frame.yaxis.x:.{point_precision}f}',
                "Y": f'{self.blank_frame.yaxis.y:.{point_precision}f}',
                "Z": f'{self.blank_frame.yaxis.z:.{point_precision}f}',
                }
            y_vector = ET.SubElement(position, "YVector", y_vector_vals)

            grain_direction = ET.SubElement(self._et_element, "GrainDirection", X="1", Y="0", Z="0", Align="no")
            reference_side = ET.SubElement(self._et_element, "ReferenceSide", Side="3", Align="no")
            processings = ET.SubElement(self._et_element, "Processings")

            for process in self.processes:
                processings.append(process.et_element)

            shape = ET.SubElement(self._et_element, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="true", coordIndex="")
            strings = self.shape_strings
            indexed_face_set.set("coordIndex", strings[0])
            coordinate = ET.SubElement(indexed_face_set, "Coordinate", point=strings[1])
        return self._et_element

    def generate_blank_geometry(self):
        start_point = None
        min_parameter = None
        max_parameter = None
        for feature in self.trim_features:
            length_params = []
            for edge in self.beam.long_edges:
                intersection_point = intersection_line_plane(edge, Plane.from_frame(feature._geometry))[0]
                length_params.append(self.beam.centerline.closest_point(intersection_point, True))
            length_params.sort(key = lambda x: x[1])
            #self._msg.append(f'length_params = {length_params}')
            if length_params[0][1] < self.length / 2:
                min_parameter = length_params[0][1]
                start_point = length_params[0][0]
            else:
                max_parameter = length_params[-1][1]

        blank_frame_point = self.beam.long_edges[2].closest_point(start_point)# I used long_edge[2] because it is in Y and Z negative. Using that as reference puts the beam entirely in positive coordinates.
        self.blank_frame = Frame(
            blank_frame_point,
            self.frame.xaxis,
            self.frame.yaxis,
        )
        self._test.append(self.reference_frame(3))
        self.blank_length = max_parameter - min_parameter
        self.blank_geometry = Box(self.blank_length, self.width, self.height, self.blank_frame)
        self.blank_geometry.transform(Translation.from_vector(self.blank_frame.xaxis * self.blank_length * 0.5 + self.blank_frame.yaxis * self.width * 0.5 + self.blank_frame.zaxis * self.height * 0.5))

    def generate_processes(self):
        for feature in self.features:
            match feature:
                case BeamExtensionFeature():
                    pass
                case BeamTrimmingFeature():
                    self.processes.append(BTLxJackCut(feature, self))

                case other:
                    self._msg.append(f'feature type {type(feature)} not implemented')

    @property
    def trim_features(self):
        trim_features_out = []
        for feature in self.features:
            if isinstance(feature, BeamTrimmingFeature):
                trim_features_out.append(feature)
        return trim_features_out

    def reference_frame(self, number):
        number -= 1
        match number:
            case 0:
                return Frame(self.blank_frame.point, self.blank_frame.xaxis, self.blank_frame.zaxis)
            case 1:
                point = self.blank_frame.point + self.blank_frame.yaxis * self.width
                return Frame(point, self.blank_frame.xaxis, -self.blank_frame.yaxis)
            case 2:
                point = (
                    self.blank_frame.point + self.blank_frame.yaxis * self.width + self.blank_frame.zaxis * self.height
                )
                return Frame(point, self.blank_frame.xaxis, -self.blank_frame.zaxis)
            case 3:
                point = self.blank_frame.point + self.blank_frame.zaxis * self.height
                return Frame(point, self.blank_frame.xaxis, self.blank_frame.yaxis)
            case 4:
                return Frame(self.blank_frame.point, self.blank_frame.zaxis, self.blank_frame.yaxis)
            case 5:
                point = (
                    self.blank_frame.point
                    + self.blank_frame.xaxis * self.blank_length
                    + self.blank_frame.yaxis * self.width
                )
                return Frame(point, self.blank_frame.zaxis, -self.blank_frame.yaxis)
            case other:
                pass

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

class BTLxProcess:
    def __init__(self, feature, part):
        self.feature = feature
        self.part = part
        self._process = None
        self._orientation = None
        self._test = []
        self._msg = []

    @property
    def geometry(self):
        return self.feature._geometry

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
    def orientation(self):
        if self._orientation == None:
            self.part.generate_blank_geometry()
        return self._orientation

    @property
    def et_element(self):
        process_et = ET.Element(self.process_type, self.header_attributes)
        for key, val in self.process_params.items():
            child = ET.SubElement(process_et, key)
            child.text = val
        return process_et



class BTLxJackCut(BTLxProcess):
    def __init__(self, feature, part):
        super().__init__(feature, part)
        self._feature = feature
        self._process = None
        self.cut_plane = feature._geometry


        self._startX = None
        self._startY: 0
        self._start_depth: 0
        self._angle = 90
        self._inclination = 90

        self.process_type = "JackRafterCut"

        self.header_attributes = {
            "Name": "Jack cut",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "4",
            "ReferencePlaneID": "1",
        }

    @property
    def process_params(self):
        self.generate_process()
        point_precision = 3
        angle_precision = 2
        return {
            "Orientation": str(self._orientation),
            "StartX": f'{self._startX:.{point_precision}f}',
            "StartY": "0",
            "StartDepth": "0",
            "Angle": f'{self._angle:.{angle_precision}f}',
            "Inclination": f'{self._inclination:.{angle_precision}f}',
        }

    def generate_process(self):
        self.x_edge = Line.from_point_and_vector(self.part.reference_frame(1).point, self.part.reference_frame(1).xaxis)
        self._startX = (
            intersection_line_plane(self.x_edge, Plane.from_frame(self.feature._geometry))[1] * self.x_edge.length
        )
        if self._startX < self.part.blank_length / 2:
            self._orientation = "start"
        else:
            self._orientation = "end"
        angle_direction = cross_vectors(self.part.reference_frame(1).zaxis, self.geometry.normal)
        self._angle = (
            angle_vectors_signed(
                self.part.reference_frame(1).xaxis, angle_direction, self.part.reference_frame(1).zaxis
            )
            * 180
            / math.pi
        )

        self._angle = abs(self._angle)
        self._angle = 90 - (self._angle - 90)

        inclination_direction = cross_vectors(self.part.reference_frame(1).yaxis, self.geometry.normal)
        self._inclination = (
            angle_vectors_signed(self.part.reference_frame(1).zaxis, self.geometry.normal, angle_direction)
            * 180
            / math.pi
        )
        self._inclination = abs(self._inclination)
        self._inclination = 90 - (self._inclination - 90)


def get_btlx_string(assembly_json):
    assembly = compas.json_loads(assembly_json)
    btlx_ins = BTLx(assembly)
    return [str(btlx_ins), btlx_ins.test, btlx_ins.msg]
