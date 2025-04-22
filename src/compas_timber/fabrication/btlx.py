import os
import uuid
import xml.dom.minidom as MD
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import date
from datetime import datetime
from itertools import chain
from warnings import warn

import compas
from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import angle_vectors
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import correct_polyline_direction


class BTLxWriter(object):
    """Class for writing BTLx files from a given model.

    BTLx is a format used for representing timber fabrication data.

    Use BTLxWriter.write() to write a BTLx file from a model and a file path.

    Parameters
    ----------
    company_name : str, optional
        The name of the company. Defaults to "Gramazio Kohler Research".
    file_name : str, optional
        The name of the file. Defaults to None.
    comment : str, optional
        A comment to be included in the file. Defaults to None.


    """

    SERIALIZERS = {}

    POINT_PRECISION = 3
    ANGLE_PRECISION = 3
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

    def __init__(self, project_name=None, company_name=None, file_name=None, comment=None):
        self.company_name = company_name
        self.file_name = file_name
        self.comment = comment
        self._project_name = project_name or "COMPAS Timber Project"

    def write(self, model, file_path):
        """Writes the BTLx file to the given file path.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model object.
        file_path : str
            The file path to write the BTLx file to.

        Returns
        -------
        str
            The XML string of the BTLx file.

        See Also
        --------
        :meth:`BTLxWriter.model_to_xml`

        """
        if not file_path.endswith(".btlx"):
            file_path += ".btlx"
        btlx_string = self.model_to_xml(model)
        with open(file_path, "w") as file:
            file.write(btlx_string)
        return btlx_string

    def model_to_xml(self, model):
        """Converts the model to an XML string.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model object.

        Returns
        -------
        str
            The XML string of the BTLx file.

        See Also
        --------
        :meth:`BTLxWriter.write`

        """
        root_element = ET.Element("BTLx", self.FILE_ATTRIBUTES)
        # first child -> file_history
        file_history_element = self._create_file_history()
        # second child -> project
        project_element = self._create_project_element(model)
        root_element.extend([file_history_element, project_element])
        return MD.parseString(ET.tostring(root_element)).toprettyxml(indent="   ")

    def _create_file_history(self):
        """Creates the file history element. This method creates the initial export program element and appends it to the file history element.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The file history element.

        """
        # create file history element
        file_history = ET.Element("FileHistory")
        # create initial export program element
        file_history_attibutes = self._get_file_history_attributes()
        file_history.append(ET.Element("InitialExportProgram", file_history_attibutes))
        return file_history

    def _get_file_history_attributes(self):
        """Generates the file history attributes with the current date and time."""
        file_history_attributes = OrderedDict(
            [
                ("CompanyName", self.company_name or "Gramazio Kohler Research"),
                ("ProgramName", "COMPAS_Timber"),
                ("ProgramVersion", "Compas: {}".format(compas.__version__)),
                ("ComputerName", "{}".format(os.getenv("computername"))),
                ("UserName", "{}".format(os.getenv("USERNAME"))),
                ("FileName", self.file_name or ""),
                ("Date", "{}".format(date.today())),
                ("Time", "{}".format(datetime.now().strftime("%H:%M:%S"))),
                ("Comment", self.comment or ""),
            ]
        )
        return file_history_attributes

    def _create_project_element(self, model):
        """Creates the project element. This method creates the parts element and appends it to the project element.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The project element.

        """
        # create project element
        project_element = ET.Element("Project", Name=self._project_name)
        # create parts element
        parts_element = ET.SubElement(project_element, "Parts")
        # create part elements for each beam
        elements = chain(model.beams, model.plates)
        for i, element in enumerate(elements):
            part_element = self._create_part(element, i)
            parts_element.append(part_element)
        return project_element

    def _create_part(self, element, order_num):
        """Creates a part element. This method creates the processing elements and appends them to the part element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element` # TODO: not really
            The element object.
        num : int
            The order number of the part.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The part element.

        """
        # create part element
        part = BTLxPart(element, order_num=order_num)
        part_element = ET.Element("Part", part.attr)
        part_element.extend([part.et_transformations, part.et_grain_direction, part.et_reference_side])
        # create processings element for the part if there are any
        if element.features:
            processings_element = ET.Element("Processings")
            for feature in element.features:
                # TODO: This is a temporary hack to skip features from the old system that don't generate a processing, until they are removed or updated.
                if hasattr(feature, "PROCESSING_NAME"):
                    processing_element = self._create_processing(feature)
                    processings_element.append(processing_element)
                else:
                    warn("Unsupported feature will be skipped: {}".format(feature))
            part_element.append(processings_element)
        if element.is_beam and element._geometry:
            # TODO: implement this for plates as well. Brep.from_extrusion seems to have incorrect number of faces regardless of input curve.
            part_element.append(part.et_shape)
        return part_element

    def _create_processing(self, processing):
        """Creates a processing element. This method creates the subprocess elements and appends them to the processing element.

        Parameters
        ----------
        processing : :class:`~compas_timber.fabrication.btlx.BTLxProcessing`
            The processing object.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The processing element.

        """
        processing_params = processing.params
        params_dict = processing_params.as_dict()

        processing_element = ET.Element(
            processing_params.header_attributes["Name"],
            processing_params.header_attributes,
        )

        for key, value in params_dict.items():
            if isinstance(value, dict):
                # childless element:
                # <Element key1="value1" key2="value2" />
                param = ET.Element(key)
                for sub_key, sub_value in value.items():
                    param.set(sub_key, sub_value)

            elif isinstance(value, str):
                # single value element:
                # <Element>value</Element>
                param = ET.Element(key)
                param.text = value

            else:
                # complex parameter:
                # <Element><SubElement1 /><SubElement2 /></Element>
                param = self._element_from_complex_param(value)
            processing_element.append(param)

        if processing.subprocessings:  # TODO: expose this in Params as well so this logic only interacts with it
            for subprocessing in processing.subprocessings:
                processing_element.append(self._create_processing(subprocessing))
        return processing_element

    def _element_from_complex_param(self, param):
        serializer = self.SERIALIZERS.get(type(param).__name__, None)
        if not serializer:
            raise ValueError("No serializer found for type: {}".format(type(param)))
        return serializer(param)

    @classmethod
    def register_type_serializer(cls, type_, serializer):
        """Register a type and its serializer.

        Parameters
        ----------
        type_ : type
            The type to be serialized.
        serializer : callable
            The serializer function. Takes an instance of `type_` and returns an XML element which correspondes with it.

        """
        cls.SERIALIZERS[type_] = serializer


class BTLxPart(object):
    """Class representing a BTLx part. This acts as a wrapper for an Element object.

    Parameters
    ----------
    element : :class:`~compas_model.elements.Element`  # TODO: not really, make BTLx Element parent class
        The element object.

    Attributes
    ----------
    attr : dict
        The attributes of the BTLx part.
    element : :class:`~compas_model.elements.Element`
        The element object.
    key : str
        The key of the element object.
    length : float
        The length of the element.
    width : float
        The width of the element.
    height : float
        The height of the element.
    frame : :class:`~compas.geometry.Frame`
        The frame of the BTLxPart at the corner of the blank box that puts the blank geometry in positive coordinates.
    blank : :class:`~compas.geometry.Box`
        The blank of the element.
    blank_frame : :class:`~compas.geometry.Frame`
        The frame of the blank.
    blank_length : float
        The blank length of the element.
    processings : list
        A list of the processings applied to the element.

    """

    def __init__(self, element, order_num):
        self.element = element
        self.order_num = order_num
        self.length = element.blank_length
        self.width = element.width
        self.height = element.height
        self.frame = element.ref_frame
        self.processings = []
        self._et_element = None
        self._shape_strings = None

    @property
    def part_guid(self):
        return str(self.element.guid)

    @property
    def et_grain_direction(self):
        return ET.Element("GrainDirection", X="1", Y="0", Z="0", Align="no")

    @property
    def et_reference_side(self):
        return ET.Element("ReferenceSide", Side="1", Align="no")

    def ref_side_from_face(self, element_face):
        """Finds the one-based index of the reference side with normal that matches the normal of the given element face.

        This essentially translates between the element face reference system to the BTLx side reference system.

        Parameters
        ----------
        element_face : :class:`~compas.geometry.Frame`
            The frame of an element face from element.faces.

        Returns
        -------
        key : str
            The key(index 1-6) of the reference surface.

        """
        for index, ref_side in enumerate(self.element.ref_sides):
            angle = angle_vectors(ref_side.normal, element_face.normal, deg=True)
            if TOL.is_zero(angle):
                return index + 1  # in BTLx face indices are one-based
        raise ValueError("Given element face does not match any of the reference surfaces.")

    @property
    def attr(self):
        return {
            "SingleMemberNumber": str(self.order_num),
            "AssemblyNumber": "",
            "OrderNumber": str(self.order_num),
            "Designation": "",
            "Annotation": "",
            "Storey": "",
            "Group": "",
            "Package": "",
            "Material": "",
            "TimberGrade": "",
            "QualityGrade": "",
            "Count": "1",
            "Length": "{:.{prec}f}".format(self.length, prec=BTLxWriter.POINT_PRECISION),
            "Height": "{:.{prec}f}".format(self.height, prec=BTLxWriter.POINT_PRECISION),
            "Width": "{:.{prec}f}".format(self.width, prec=BTLxWriter.POINT_PRECISION),
            "Weight": "0",
            "ProcessingQuality": "automatic",
            "StoreyType": "",
            "ElementNumber": "00",
            "Layer": "0",
            "ModuleNumber": "",
        }

    def et_point_vals(self, point):
        """Returns the ET point values for a given point.

        Parameters
        ----------
        point : :class:`~compas.geometry.Point`
            The point to be converted.

        Returns
        -------
        dict
            The ET point values formatted for the ET element.

        """
        return {
            "X": "{:.{prec}f}".format(point.x, prec=BTLxWriter.POINT_PRECISION),
            "Y": "{:.{prec}f}".format(point.y, prec=BTLxWriter.POINT_PRECISION),
            "Z": "{:.{prec}f}".format(point.z, prec=BTLxWriter.POINT_PRECISION),
        }

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
        indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="false", coordIndex=self.shape_strings[0])
        indexed_face_set.append(ET.Element("Coordinate", {"point": self.shape_strings[1]}))
        return shape

    @property
    def shape_strings(self):
        """Generates the shape strings for the BTLxPart. Only works in environments where the element.geometry Brep is available.

        returns
        -------
        list
            A list of two strings, the first string is the brep indices string, the second string is the brep vertices string.
        """

        if not self._shape_strings:
            brep_vertex_points = []
            brep_indices = []
            for face in self.element.geometry.faces:
                pts = []
                frame = face.surface.frame_at(0.5, 0.5)
                edges = face.boundary.edges[1:]
                pts = [face.boundary.edges[0].start_vertex.point, face.boundary.edges[0].end_vertex.point]
                overflow = len(edges)
                while edges and overflow > 0:
                    for i, edge in enumerate(edges):
                        if (not edge.is_line) or ((edge.start_vertex.point in pts) and (edge.end_vertex.point in pts)):  # edge endpoints already in pts
                            edges.pop(i)
                        elif TOL.is_allclose(edge.start_vertex.point, pts[-1]) and (edge.end_vertex.point not in pts):  # edge.start_vertex is the last point in pts
                            pts.append(edges.pop(i).end_vertex.point)
                        elif TOL.is_allclose(edge.end_vertex.point, pts[-1]) and (edge.start_vertex.point not in pts):  # edge.end_vertex is the last point in pts
                            pts.append(edges.pop(i).start_vertex.point)
                    overflow -= 1
                pts = correct_polyline_direction(pts, frame.normal)

                if len(pts) != len(face.edges):
                    print("edge count doesnt match point count, BTLxPart shape will be incorrect")

                if len(pts) > 2:
                    for pt in pts:
                        if pt in brep_vertex_points:
                            brep_indices.append(brep_vertex_points.index(pt))
                        else:
                            brep_indices.append(len(brep_vertex_points))
                            brep_vertex_points.append(pt)
                    brep_indices.append(-1)

            brep_indices_string = ""
            for index in brep_indices:
                brep_indices_string += str(index) + " "

            brep_vertices_string = ""
            for point in brep_vertex_points:
                xform = Transformation.from_frame_to_frame(self.frame, Frame((0, 0, 0), (1, 0, 0), (0, 1, 0)))
                point.transform(xform)
                brep_vertices_string += "{:.{prec}f} {:.{prec}f} {:.{prec}f} ".format(point.x, point.y, point.z, prec=3)
                brep_vertices_string = brep_vertices_string.replace("-", "")

            self._shape_strings = [brep_indices_string, brep_vertices_string]
        return self._shape_strings


def contour_to_xml(contour):
    """Converts a contour to an XML element.

    Parameters
    ----------
    contour : :class:`Contour`
        The contour to be converted.

    Returns
    -------
    :class:`~xml.etree.ElementTree.Element`
        The element which represents the contour.

    """

    root = ET.Element("Contour")
    if contour.depth:
        root.set("Depth", "{:.{prec}f}".format(contour.depth, prec=BTLxWriter.POINT_PRECISION))
    if contour.depth_bounded:
        root.set("DepthBounded", "yes" if contour.depth_bounded else "no")

    start = contour.polyline[0]
    start_point = ET.SubElement(root, "StartPoint")
    start_point.set("X", "{:.{prec}f}".format(start.x, prec=BTLxWriter.POINT_PRECISION))
    start_point.set("Y", "{:.{prec}f}".format(start.y, prec=BTLxWriter.POINT_PRECISION))
    start_point.set("Z", "{:.{prec}f}".format(start.z, prec=BTLxWriter.POINT_PRECISION))

    if len(contour.inclination) == 1:  # single Inclination for all segments
        root.set("Inclination", "{:.{prec}f}".format(contour.inclination[0], prec=BTLxWriter.ANGLE_PRECISION))
        for point in contour.polyline[1:]:
            line = ET.SubElement(root, "Line")
            end_point = ET.SubElement(line, "EndPoint")
            end_point.set("X", "{:.{prec}f}".format(point[0], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Y", "{:.{prec}f}".format(point[1], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Z", "{:.{prec}f}".format(point[2], prec=BTLxWriter.POINT_PRECISION))

    else:  # one Inclination value per segment
        for point, inc in zip(contour.polyline[1:], contour.inclination):
            line = ET.SubElement(root, "Line", {"Inclination": "{:.{prec}f}".format(inc, prec=BTLxWriter.ANGLE_PRECISION)})
            end_point = ET.SubElement(line, "EndPoint")
            end_point.set("X", "{:.{prec}f}".format(point[0], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Y", "{:.{prec}f}".format(point[1], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Z", "{:.{prec}f}".format(point[2], prec=BTLxWriter.POINT_PRECISION))

    return root


def dual_contour_to_xml(contour):
    """Converts a contour to an XML element.

    Parameters
    ----------
    contour : :class:`DualContour`
        The DualContour to be converted.

    Returns
    -------
    :class:`~xml.etree.ElementTree.Element`
        The element which represents the contour.

    """
    root = ET.Element("DualContour")
    principal_contour = ET.SubElement(root, "PrincipalContour")
    associated_contour = ET.SubElement(root, "AssociatedContour")
    for polyline, et_contour in zip([contour.principal_contour, contour.associated_contour], [principal_contour, associated_contour]):
        start = polyline[0]
        start_point = ET.SubElement(et_contour, "StartPoint")
        start_point.set("X", "{:.{prec}f}".format(start.x, prec=BTLxWriter.POINT_PRECISION))
        start_point.set("Y", "{:.{prec}f}".format(start.y, prec=BTLxWriter.POINT_PRECISION))
        start_point.set("Z", "{:.{prec}f}".format(start.z, prec=BTLxWriter.POINT_PRECISION))

        for point in polyline[1:]:
            line = ET.SubElement(et_contour, "Line")
            end_point = ET.SubElement(line, "EndPoint")
            end_point.set("X", "{:.{prec}f}".format(point[0], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Y", "{:.{prec}f}".format(point[1], prec=BTLxWriter.POINT_PRECISION))
            end_point.set("Z", "{:.{prec}f}".format(point[2], prec=BTLxWriter.POINT_PRECISION))
    return root


class BTLxProcessing(Data):
    """Base class for BTLx Processing.

    Attributes
    ----------
    ref_side_index : int
        The reference side, zero-based, index of the element to be cut. 0-5 correspond to RS1-RS6.
    priority : int
        The priority of the process.
    process_id : int
        The process ID.
    PROCESSING_NAME : str
        The name of the process.

    """

    @property
    def __data__(self):
        return {"ref_side_index": self.ref_side_index, "priority": self.priority, "process_id": self.process_id}

    def __init__(self, ref_side_index=None, priority=0, process_id=0):
        super(BTLxProcessing, self).__init__()
        self.ref_side_index = ref_side_index
        self._priority = priority
        self._process_id = process_id
        self.subprocessings = None

    @property
    def priority(self):
        return self._priority

    @property
    def process_id(self):
        return self._process_id

    @property
    def PROCESSING_NAME(self):
        raise NotImplementedError("PROCESSING_NAME must be implemented as class attribute in subclasses!")

    def add_subprocessing(self, subprocessing):
        """Add a nested subprocessing."""
        if not self.subprocessings:
            self.subprocessings = []
        self.subprocessings.append(subprocessing)


class BTLxProcessingParams(object):
    """Base class for BTLx processing parameters. This creates the dictionary of key-value pairs for the processing as expected by the BTLx file format.

    Parameters
    ----------
    instance : :class:`BTLxProcessing`
        The instance of the processing to create parameters for.

    """

    def __init__(self, instance):
        self._instance = instance

    @property
    def header_attributes(self):
        result = OrderedDict()
        result["Name"] = self._instance.PROCESSING_NAME
        result["Process"] = "yes"
        result["Priority"] = str(self._instance.priority)
        result["ProcessID"] = str(self._instance.process_id)
        result["ReferencePlaneID"] = str(self._instance.ref_side_index + 1)
        return result

    def as_dict(self):
        """Returns the processing parameters as a dictionary.

        Returns
        -------
        dict
            The processing parameters as a dictionary.
        """
        raise NotImplementedError("as_dict must be implemented in subclasses!")


class OrientationType(object):
    """Enum for the orientation of the cut.

    Attributes
    ----------
    START : literal("start")
        The start of the element is cut away.
    END : literal("end")
        The end of the element is cut away.
    """

    START = "start"
    END = "end"


class StepShapeType(object):
    """Enum for the step shape of the cut.

    Attributes
    ----------
    STEP : literal("step")
        A step shape.
    HEEL : literal("heel")
        A heel shape.
    TAPERED_HEEL : literal("taperedheel")
        A tapered heel shape.
    DOUBLE : literal("double")
        A double shape.
    """

    STEP = "step"
    HEEL = "heel"
    TAPERED_HEEL = "taperedheel"
    DOUBLE = "double"


class TenonShapeType(object):
    """Enum for the tenon shape of the cut.

    Attributes
    ----------
    AUTOMATIC : literal("automatic")
        Automatic tenon shape.
    SQUARE : literal("square")
        Square tenon shape.
    ROUND : literal("round")
        Round tenon shape.
    ROUNDED : literal("rounded")
        Rounded tenon shape.
    RADIUS : literal("radius")
        Radius tenon shape.
    """

    AUTOMATIC = "automatic"
    SQUARE = "square"
    ROUND = "round"
    ROUNDED = "rounded"
    RADIUS = "radius"


class LimitationTopType(object):
    """Enum for the top limitation of the cut.

    Attributes
    ----------
    LIMITED : literal("limited")
        Limitation to the cut.
    UNLIMITED : literal("unlimited")
        No limit to the cut.
    POCKET : literal("pocket")
        Pocket like limitation to the cut.
    """

    LIMITED = "limited"
    UNLIMITED = "unlimited"
    POCKET = "pocket"


class MachiningLimits(object):
    """Configuration class for the machining limits of the cut.

    Attributes
    ----------
    EXPECTED_KEYS : set
        The expected keys for the limits dictionary.
    face_limited_start : bool
        Limit the start face.
    face_limited_end : bool
        Limit the end face.
    face_limited_front : bool
        Limit the front face.
    face_limited_back : bool
        Limit the back face.
    face_limited_top : bool
        Limit the top face.
    face_limited_bottom : bool
        Limit the bottom face.

    """

    EXPECTED_KEYS = [
        "FaceLimitedStart",
        "FaceLimitedEnd",
        "FaceLimitedFront",
        "FaceLimitedBack",
        "FaceLimitedTop",
        "FaceLimitedBottom",
    ]

    def __init__(self):
        self.face_limited_start = True
        self.face_limited_end = True
        self.face_limited_front = True
        self.face_limited_back = True
        self.face_limited_top = True
        self.face_limited_bottom = True

    @property
    def limits(self):
        """Dynamically generate the limits dictionary with boolean values from instance attributes."""
        return {
            "FaceLimitedStart": self.face_limited_start,
            "FaceLimitedEnd": self.face_limited_end,
            "FaceLimitedFront": self.face_limited_front,
            "FaceLimitedBack": self.face_limited_back,
            "FaceLimitedTop": self.face_limited_top,
            "FaceLimitedBottom": self.face_limited_bottom,
        }


class EdgePositionType(object):
    """Enum for the edge position of the cut.

    Attributes
    ----------
    REFEDGE : literal("refedge")
        Reference edge.
    OPPEDGE : literal("oppedge")
        Opposite edge.
    """

    REFEDGE = "refedge"
    OPPEDGE = "oppedge"


class AlignmentType(object):
    """Enum for the alignment of the cut.
    Attributes
    ----------
    TOP : literal("top")
        Top alignment.
    BOTTOM : literal("bottom")
        Bottom alignment.
    LEFT : literal("left")
        Left alignment.
    RIGHT : literal("right")
        Right alignment.
    CENTER : literal("center")
        Center alignment.
    """

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class Contour(Data):
    """Represens the generic contour for specific free contour processings.

    TODO: add point attributes for other types like NailContour

    Parameters
    ----------
    depth : float
        The depth of the contour.
    depth_bounded : bool
        If True, the depth is bounded.
    inclination : float
        The inclination of the contour.
    polyline : :class:`compas.geometry.Polyline`
        The polyline of the contour.
    """

    def __init__(self, polyline, depth=None, depth_bounded=True, inclination=None):
        super(Contour, self).__init__()
        self.polyline = polyline
        self.depth = depth
        self.depth_bounded = depth_bounded
        self.inclination = inclination

    @property
    def __data__(self):
        return {"polyline": self.polyline, "depth": self.depth, "depth_bounded": self.depth_bounded, "inclination": self.inclination}


BTLxWriter.register_type_serializer(Contour.__name__, contour_to_xml)


class DualContour(Data):
    """Represens the generic contour for specific free contour processings.

    TODO: add point attributes for other types like NailContour

    Parameters
    ----------
    principal_contour : :class:`compas.geometry.Polyline`
        The principal contour of the dual contour.
    associated_contour : :class:`compas.geometry.Polyline`
        The associated contour of the dual contour. Must have same number of segments as `principal_contour`.
    depth_bounded : bool
        If True, the depth is bounded.
    """

    def __init__(self, principal_contour, associated_contour, depth_bounded=None):
        super(DualContour, self).__init__()
        self.principal_contour = principal_contour
        self.associated_contour = associated_contour
        self.depth_bounded = depth_bounded

    @property
    def __data__(self):
        return {"principal_contour": self.principal_contour, "associated_contour": self.associated_contour, "depth_bounded": self.depth_bounded}


BTLxWriter.register_type_serializer(DualContour.__name__, dual_contour_to_xml)


class BTLxFromGeometryDefinition(Data):
    """Container linking a BTLx Process Type and generator function to an input geometry.
    This allows delaying the actual applying of features to a downstream component.

    Parameters
    ----------
    processing : class
        The BTLx Processing class.
    geometries : list of :class:`~compas.geometry.Geometry`
        The geometries to be used as input for the processing.
    elements : list of :class:`~compas_timber.elements.Element`
        The elements to be used as input for the processing.

    Attributes
    processing : class
        The BTLx Processing class.
    geometries : list of :class:`~compas.geometry.Geometry`
        The geometries to be used as input for the processing.
    elements : list of :class:`~compas_timber.elements.Element`
        The elements to be used as input for the processing.
    """

    def __init__(self, processing, geometries, elements=None, **kwargs):
        super(BTLxFromGeometryDefinition, self).__init__()
        self.processing = processing
        self.geometries = geometries if isinstance(geometries, list) else [geometries]
        if elements:
            self.elements = elements if isinstance(elements, list) else [elements]
        else:
            self.elements = []
        self.kwargs = kwargs or {}

    @property
    def __data__(self):
        return {"processing": self.processing, "geometries": self.geometries, "elements": self.elements, "kwargs": self.kwargs}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["processing"], data["geometries"], data["elements"], **data["kwargs"])

    def __repr__(self):
        return "{}({}, {})".format(BTLxFromGeometryDefinition.__name__, self.processing, self.geometries)

    def ToString(self):
        return repr(self)

    def transform(self, transformation):
        for geo in self.geometries:
            geo.transform(transformation)

    def transformed(self, transformation):
        copy = self.copy()
        copy.transform(transformation)
        return copy

    def feature_from_element(self, element):
        try:
            return self.processing.from_shapes_and_element(*self.geometries, element=element, **self.kwargs)
        except Exception as ex:
            raise FeatureApplicationError(self.geometries, element.blank, str(ex))
