import os
from sqlite3 import paramstyle
import uuid
import xml.dom.minidom as MD
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import date
from datetime import datetime
from warnings import warn

import compas
from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import angle_vectors
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError


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
        for i, beam in enumerate(model.beams):  # TODO: we need to add at least Plates to this too.
            part_element = self._create_part(beam, i)
            parts_element.append(part_element)
        return project_element

    def _create_part(self, beam, order_num):
        """Creates a part element. This method creates the processing elements and appends them to the part element.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam object.
        num : int
            The order number of the part.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The part element.

        """
        # create part element
        part = BTLxPart(beam, order_num=order_num)
        part_element = ET.Element("Part", part.attr)
        part_element.extend([part.et_transformations, part.et_grain_direction, part.et_reference_side])
        # create processings element for the part if there are any
        if beam.features:
            processings_element = ET.Element("Processings")
            for feature in beam.features:
                # TODO: This is a temporary hack to skip features from the old system that don't generate a processing, until they are removed or updated.
                if hasattr(feature, "PROCESSING_NAME"):
                    processing_element = self._create_processing(feature)
                    processings_element.append(processing_element)
                else:
                    warn("Unsupported feature will be skipped: {}".format(feature))
            part_element.append(processings_element)
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
        # create processing element
        processing_element = ET.Element(
            processing.PROCESSING_NAME,
            processing.header_attributes,
        )
        # create parameter subelements
        for key, value in processing.params_dict.items():
            if key not in processing.header_attributes:
                child = ET.SubElement(processing_element, key)
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        child.set(sub_key, sub_value)
                else:
                    child.text = str(value)
        # create subprocessing elements
        if processing.subprocessings:
            for subprocessing in processing.subprocessings:
                processing_element.append(self._create_processing(subprocessing))
        return processing_element


class BTLxPart(object):
    """Class representing a BTLx part. This acts as a wrapper for a Beam object.

    Parameters
    ----------
    beam : :class:`~compas_timber.elements.Beam`
        The beam object.

    Attributes
    ----------
    attr : dict
        The attributes of the BTLx part.
    beam : :class:`~compas_timber.elements.Beam`
        The beam object.
    key : str
        The key of the beam object.
    length : float
        The length of the beam.
    width : float
        The width of the beam.
    height : float
        The height of the beam.
    frame : :class:`~compas.geometry.Frame`
        The frame of the BTLxPart at the corner of the blank box that puts the blank geometry in positive coordinates.
    blank : :class:`~compas.geometry.Box`
        The blank of the beam.
    blank_frame : :class:`~compas.geometry.Frame`
        The frame of the blank.
    blank_length : float
        The blank length of the beam.
    processings : list
        A list of the processings applied to the beam.
    et_element : :class:`~xml.etree.ElementTree.Element`
        The ET element of the BTLx part.

    """

    def __init__(self, beam, order_num):
        self.beam = beam
        self.order_num = order_num
        self.length = beam.blank_length
        self.width = beam.width
        self.height = beam.height
        self.frame = beam.ref_frame
        self.blank_length = beam.blank_length
        self.processings = []
        self._et_element = None

    @property
    def part_guid(self):
        return str(self.beam.guid)

    @property
    def et_grain_direction(self):
        return ET.Element("GrainDirection", X="1", Y="0", Z="0", Align="no")

    @property
    def et_reference_side(self):
        return ET.Element("ReferenceSide", Side="1", Align="no")

    def ref_side_from_face(self, beam_face):
        """Finds the one-based index of the reference side with normal that matches the normal of the given beam face.

        This essentially translates between the beam face reference system to the BTLx side reference system.

        Parameters
        ----------
        beam_face : :class:`~compas.geometry.Frame`
            The frame of a beam face from beam.faces.

        Returns
        -------
        key : str
            The key(index 1-6) of the reference surface.

        """
        for index, ref_side in enumerate(self.beam.ref_sides):
            angle = angle_vectors(ref_side.normal, beam_face.normal, deg=True)
            if TOL.is_zero(angle):
                return index + 1  # in BTLx face indices are one-based
        raise ValueError("Given beam face does not match any of the reference surfaces.")

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
            "Length": "{:.{prec}f}".format(self.blank_length, prec=BTLxWriter.POINT_PRECISION),
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
    def et_element(self):
        if self._et_element is None:
            self._et_element = ET.Element("Part", self.attr)
            self._shape_strings = None
            self._et_element.append(self.et_transformations)
            self._et_element.append(ET.Element("GrainDirection", X="1", Y="0", Z="0", Align="no"))
            self._et_element.append(ET.Element("ReferenceSide", Side="1", Align="no"))
            processings_et = ET.Element("Processings")
            if self.processings:  # otherwise there will be an empty <Processings/> tag
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
        # TODO: this need some cleanup, potentially removal
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
                brep_vertices_string += "{:.{prec}f} {:.{prec}f} {:.{prec}f} ".format(point.x, point.y, point.z, prec=BTLxWriter.POINT_PRECISION)
            self._shape_strings = [brep_indices_string, brep_vertices_string]
        return self._shape_strings


class BTLxProcessing(Data):
    """Base class for BTLx Processing.

    Attributes
    ----------
    ref_side_index : int
        The reference side, zero-based, index of the beam to be cut. 0-5 correspond to RS1-RS6.
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

    def __init__(self, ref_side_index=0, priority=0, process_id=0):
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

    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element."""
        return {
            "Name": self.PROCESSING_NAME,
            "Priority": str(self.priority),
            "Process": "yes",
            "ProcessID": str(self.process_id),
            "ReferencePlaneID": str(self.ref_side_index + 1),
        }

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

    def as_dict(self):
        """Returns the processing parameters as a dictionary.

        Returns
        -------
        dict
            The processing parameters as a dictionary.
        """
        result = OrderedDict()
        result["Name"] = self._instance.PROCESSING_NAME
        result["Process"] = "yes"
        result["Priority"] = str(self._instance.priority)
        result["ProcessID"] = str(self._instance.process_id)
        result["ReferencePlaneID"] = str(self._instance.ref_side_index + 1)
        return result


class OrientationType(object):
    """Enum for the orientation of the cut.

    Attributes
    ----------
    START : literal("start")
        The start of the beam is cut away.
    END : literal("end")
        The end of the beam is cut away.
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


class DeferredBTLxProcessing(Data):
    """Deferred BTLx Processing class for delayed processing of geometry.

    Parameters
    ----------
    processing : class
        The BTLx Processing class.
    geometries : list of :class:`~compas.geometry.Geometry`
        The geometries to be used as input for the processing.
    elements : list of :class:`~compas_timber.elements.Element`
        The elements to be used as input for the processing.

    """

    def __init__(self, processing_type = None, elements = None, **params):   #direct definition of BTLx Parameters
        if elements is None:
            self.elements = []
        else:
            self.elements = elements if isinstance(elements, list) else [elements]
        self.params = params
        self.geometries = []
        self.processing_type = processing_type

    @classmethod
    def from_shapes(cls, shapes, **kwargs):
        raise NotImplementedError("Processing from geometry should be implemented on specific DeferredBTLxProcessing classes.")

    @property
    def __data__(self):
        return {"geometries": self.geometries, "elements": self.elements, "kwargs": self.params}

    def transform(self, transformation):
        for geo in self.geometries:
            geo.transform(transformation)

    def transformed(self, transformation):
        copy = self.copy()
        copy.transform(transformation)

    def feature_from_element(self, element):
        if self.geometries:
            raise NotImplementedError("Processing from geometry should be implemented on specific Processing classes.")
        else:
            return self.processing_type(**self.params)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.geometries, self.elements)

    def __str__(self):
        print(self.elements)
        return ("DeferredBTLxProcessing of type {} with geometries {} and elements {}".format(
            self.__class__,
            [geo.__class__ for geo in self.geometries],
            [el.__class__ for el in self.elements]
            ))

    def ToString(self):
        return self.__str__()
