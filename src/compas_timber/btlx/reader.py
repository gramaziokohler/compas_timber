import uuid
import xml.etree.ElementTree as ET
from warnings import warn

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.errors import BTLxParsingError
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication import Contour
from compas_timber.fabrication import DualContour
from compas_timber.model import TimberModel
from compas_timber.utils import get_leaf_subclasses


class BTLxReader(object):
    """Class for reading BTLx files and creating a TimberModel.

    BTLx is a format used for representing timber fabrication data.

    Use BTLxReader.read() to read a BTLx file and return a TimberModel.

    .. note::
        TODO: Add optional tolerance parameter to allow users to specify model units (MM or M).
        This would enable automatic scaling of geometry when creating models in different units.

    Attributes
    ----------
    errors : list
        A list of errors encountered during parsing.

    """

    DESERIALIZERS = {}  # Maps child element names to deserializer functions

    def __init__(self):
        self._errors = []
        self._processing_types = {cls.PROCESSING_NAME: cls for cls in get_leaf_subclasses(BTLxProcessing)}

    @property
    def errors(self):
        """Get the list of errors encountered during parsing."""
        return self._errors

    def print_errors(self):
        """Print a summary of all errors accumulated during the last read operation."""
        if not self._errors:
            print("No errors.")
            return
        print("{} error(s) encountered during parsing:".format(len(self._errors)))
        for i, error in enumerate(self._errors, 1):
            print("  [{}] {}".format(i, error))

    @classmethod
    def register_type_deserializer(cls, type_name, deserializer):
        """Register a type and its deserializer.

        Parameters
        ----------
        type_name : str
            The name of the type to be deserialized (matching the XML element tag name).
        deserializer : callable
            The deserializer function. Takes an XML element and returns an instance of the type.

        """
        cls.DESERIALIZERS[type_name] = deserializer

    def read(self, file_path):
        """Read a BTLx file and return a TimberModel.

        Parameters
        ----------
        file_path : str
            The path to the BTLx file to read.

        Returns
        -------
        :class:`~compas_timber.model.TimberModel`
            The timber model containing the elements and features from the BTLx file.

        """
        with open(file_path, "r") as f:
            xml_string = f.read()
        return self.xml_to_model(xml_string)

    def xml_to_model(self, xml_string):
        """Parse an XML string and return a TimberModel.

        Parameters
        ----------
        xml_string : str
            The XML string representation of a BTLx file.

        Returns
        -------
        :class:`~compas_timber.model.TimberModel`
            The timber model containing the elements and features from the BTLx file.

        """

        # Parse XML
        root = ET.fromstring(xml_string)
        # Create model with default tolerance (BTLx files are always in mm)
        model = TimberModel(tolerance=Tolerance(unit="MM"))
        # Find the Project element (wildcard namespace handles all cases)
        project = root.find(".//{*}Project")
        if project is None:
            raise ValueError("No Project element found in BTLx file")
        # Find Parts element
        parts_elem = project.find("{*}Parts")
        if parts_elem is None:
            warn("No Parts element found in BTLx file")
            return model
        # Parse each Part element
        for part_elem in parts_elem.findall("{*}Part"):
            try:
                element = self._parse_part(part_elem)
                model.add_element(element)
            except BTLxParsingError as e:
                self._errors.append(e)

        if self._errors:
            warn(
                "{} error(s) occurred during BTLx parsing. Call reader.print_errors() for details.".format(len(self._errors)),
                UserWarning,
                stacklevel=3,
            )

        return model

    def _parse_part(self, part_element):
        """Parses a part element and adds it to the model.

        Parameters
        ----------
        part_element : :class:`~xml.etree.ElementTree.Element`
            The part element to parse.

        Raises
        ------
        :class:`~compas_timber.errors.BTLxParsingError`
            If a critical attribute (dimensions, transformation, element type) cannot be parsed.
        """
        # get metadata first so it's available for error context
        annotation = part_element.attrib.get("Annotation", "")
        designation = part_element.attrib.get("Designation", "")
        single_member_number = part_element.attrib.get("SingleMemberNumber", "")

        # get dimensions
        try:
            width = float(part_element.attrib.get("Width", 0))
            height = float(part_element.attrib.get("Height", 0))
            length = float(part_element.attrib.get("Length", 0))
        except ValueError as e:
            raise BTLxParsingError("Invalid dimension value in Part: {}".format(e), part_id=single_member_number)

        # extract GUID and ref_frame from Transformation (BTLx reference frame)
        try:
            guid, ref_frame = self._parse_transformation(part_element)
        except ValueError as e:
            raise BTLxParsingError("Failed to parse transformation: {}".format(e), part_id=single_member_number)

        # get element type from designation or infer from dimensions (for BTLx files exported from COMPASTimber)
        if "Beam" in designation:
            element_type = "Beam"
        elif "Plate" in designation:
            element_type = "Plate"
        else:
            element_type = self._infer_element_type(width, height, length)

        # create element
        if element_type == "Beam":
            frame = self._ref_frame_to_beam_frame(ref_frame, width, height)
            element = Beam(frame=frame, length=length, width=width, height=height)
        elif element_type == "Plate":
            frame = self._ref_frame_to_plate_frame(ref_frame, width, height)
            element = Plate(frame=frame, length=length, width=width, thickness=height)

        # Set GUID - non-fatal: element remains valid with a new auto-generated GUID if this fails
        try:
            element._guid = uuid.UUID(guid)
        except ValueError as e:
            self._errors.append(BTLxParsingError("Invalid GUID '{}': {}".format(guid, e), part_id=single_member_number))

        # Set name and custom attribute for error context
        element.name = annotation
        element.attributes["single_member_number"] = single_member_number

        # Parse UserReferencePlanes
        self._parse_user_reference_planes(part_element, element)

        # Parse Processings
        self._parse_processings(part_element, element)
        return element

    def _parse_processings(self, part_elem, element):
        """Parse the Processings XML element and add features to the element."""
        processings_elem = part_elem.find("{*}Processings")
        if processings_elem is None:
            return

        for processing_elem in processings_elem:
            try:
                feature = self._parse_processing(processing_elem)
                element.add_feature(feature)
            except BTLxParsingError as e:
                self._errors.append(BTLxParsingError(e.message, part_id=element.attributes.get("single_member_number"), processing_type=e.processing_type))

    def _parse_processing(self, processing_elem):
        """Parse a single Processing XML element into a BTLxProcessing object."""
        processing_name = processing_elem.tag.split("}")[-1]  # Remove namespace
        processing_class = self._processing_types.get(processing_name)

        if not processing_class:
            raise BTLxParsingError("Unsupported processing type: {}".format(processing_name), processing_type=processing_name)

        # Get the processing's ATTRIBUTE_MAP for child elements
        attribute_map = getattr(processing_class, "ATTRIBUTE_MAP", {})
        header_attribute_map = getattr(processing_class, "HEADER_ATTRIBUTE_MAP", {})
        kwargs = {}

        # Parse XML attributes (header) using HEADER_ATTRIBUTE_MAP
        for xml_attr_name, xml_attr_value in processing_elem.attrib.items():
            if xml_attr_name in header_attribute_map:
                python_name, type_info = header_attribute_map[xml_attr_name]
                kwargs[python_name] = self._convert_value(xml_attr_value, type_info)
            else:
                # Unknown header attribute - skip and warn, processing can still be created
                warn("BTLx: unknown header attribute '{}' for processing type '{}'.".format(xml_attr_name, processing_name), UserWarning, stacklevel=2)

        # Parse child elements using processing's ATTRIBUTE_MAP
        for child in processing_elem:
            child_name = child.tag.split("}")[-1]  # Remove namespace
            if child_name in attribute_map:
                attr_spec = attribute_map[child_name]
                # Extract python_name and type_info from AttributeSpec
                python_name = attr_spec.python_name
                type_info = attr_spec.type

                # Branch 1: Element with attributes → dict
                # <Element key1="value1" key2="value2" />
                if len(child.attrib) > 0 and not (child.text and child.text.strip()) and len(child) == 0:
                    # Build dict from XML attributes - values stay as strings
                    xml_attr_dict = {xml_attr_name: xml_attr_value for xml_attr_name, xml_attr_value in child.attrib.items()}
                    # The from_dict method is responsible for converting string values to appropriate types
                    kwargs[python_name] = type_info.from_dict(xml_attr_dict)

                # Branch 2: Simple text element → str with type conversion
                # <Element>value</Element>
                elif child.text and child.text.strip() and len(child) == 0:
                    xml_text_value = child.text.strip()
                    # Use type_info for conversion via _convert_value
                    kwargs[python_name] = self._convert_value(xml_text_value, type_info)

                # Branch 3: Complex element with children → use deserializer
                # <Element><SubElement1 /><SubElement2 /></Element>
                else:
                    deserializer = self.DESERIALIZERS.get(child_name, None)
                    if not deserializer:
                        raise BTLxParsingError("No deserializer found for type: {}".format(child_name), processing_type=processing_name)
                    kwargs[python_name] = deserializer(child)

        # Create processing instance
        try:
            return processing_class(**kwargs)
        except Exception as e:
            raise BTLxParsingError("Failed to instantiate {}: {}".format(processing_name, e), processing_type=processing_name)

    @staticmethod
    def _convert_value(value, type_info):
        """Converts XML string values to Python types using the provided type information.

        Parameters
        ----------
        value : str
            The string value from XML.
        type_info : type or callable
            The type or converter function to use for conversion.
            Can be: bool, int, float, str, or a callable converter.

        Returns
        -------
        int, float, bool, str, or any
            The converted value.
        """
        # Handle bool specially for BTLx "yes"/"no" strings
        if type_info is bool:
            return value.lower() in ["yes", "true"]

        # Handle callable converters (custom)
        if callable(type_info):
            return type_info(value)

        # Handle standard types (int, float, str)
        return type_info(value)

    def _parse_user_reference_planes(self, part_elem, element):
        """Parse the UserReferencePlanes XML element and add planes to the element.

        Planes are stored in local ref_frame coordinates in the BTLx file.
        They are transformed back to world (model) coordinates using the
        element's ref_frame before being added to the element.
        """
        planes_elem = part_elem.find("{*}UserReferencePlanes")
        if planes_elem is None:
            return

        for plane_elem in planes_elem.findall("{*}UserReferencePlane"):
            try:
                plane_id = int(plane_elem.get("ID"))
                position = plane_elem.find("{*}Position")
                ref_point = position.find("{*}ReferencePoint")
                x_vector = position.find("{*}XVector")
                y_vector = position.find("{*}YVector")

                local_point = Point(
                    float(ref_point.get("X")),
                    float(ref_point.get("Y")),
                    float(ref_point.get("Z")),
                )
                xaxis = Vector(
                    float(x_vector.get("X")),
                    float(x_vector.get("Y")),
                    float(x_vector.get("Z")),
                )
                yaxis = Vector(
                    float(y_vector.get("X")),
                    float(y_vector.get("Y")),
                    float(y_vector.get("Z")),
                )

                local_frame = Frame(local_point, xaxis, yaxis)
                # Planes in the BTLx are in local ref_frame space; transform back to world
                T = Transformation.from_frame(element.ref_frame)
                world_frame = local_frame.transformed(T)

                element.add_user_ref_plane(world_frame, ID=plane_id)
            except Exception as e:
                self._errors.append(
                    BTLxParsingError(
                        "Failed to parse UserReferencePlane ID={}: {}".format(plane_elem.get("ID", "?"), e),
                        part_id=element.attributes.get("single_member_number"),
                    )
                )

    def _parse_transformation(self, part_elem):
        """Extract GUID and Frame from a Part's Transformation element."""
        # Find Transformation element (wildcard namespace)
        trans_elem = part_elem.find("{*}Transformations/{*}Transformation")
        if trans_elem is None:
            raise ValueError("No Transformation element found in Part")

        # Extract GUID (remove curly braces)
        guid_str = trans_elem.get("GUID", "")
        guid = guid_str.strip("{}")

        # Find Position element
        position = trans_elem.find("{*}Position")
        if position is None:
            raise ValueError("No Position element found in Transformation")

        # Extract point and vectors
        ref_point = position.find("{*}ReferencePoint")
        x_vector = position.find("{*}XVector")
        y_vector = position.find("{*}YVector")

        # Parse point (apply scale factor to coordinates)
        point = Point(
            float(ref_point.get("X")),
            float(ref_point.get("Y")),
            float(ref_point.get("Z")),
        )

        # Parse vectors (no scale factor - they're directional)
        xaxis = Vector(
            float(x_vector.get("X")),
            float(x_vector.get("Y")),
            float(x_vector.get("Z")),
        )

        yaxis = Vector(
            float(y_vector.get("X")),
            float(y_vector.get("Y")),
            float(y_vector.get("Z")),
        )

        # Create Frame (ZVector will be computed automatically)
        frame = Frame(point, xaxis, yaxis)

        return guid, frame

    def _ref_frame_to_beam_frame(self, ref_frame, width, height):
        """Convert BTLx reference frame to element centerline frame."""

        # The BTLx reference frame has its origin at the bottom-far corner of the blank,
        # with axes: X=grain/length, Y=height, Z=width.

        # The element centerline frame has its origin at the centerline start,
        # with axes: X=length, Y=width, Z=height.

        centerline_origin = ref_frame.point + width / 2.0 * ref_frame.zaxis + height / 2.0 * ref_frame.yaxis
        centerline_xaxis = ref_frame.xaxis
        centerline_yaxis = -ref_frame.zaxis

        return Frame(centerline_origin, centerline_xaxis, centerline_yaxis)

    def _ref_frame_to_plate_frame(self, btlx_ref_frame, width, thickness):
        """Convert BTLx reference frame to Plate frame."""

        # The BTLx reference frame has its origin at a corner of the blank,
        # with axes: X=grain/length, Y=thickness (height), Z=width.

        # The Plate frame has its origin at a corner of the blank,
        # with axes: X=length, Y=width, Z=thickness.

        plate_origin = btlx_ref_frame.point + btlx_ref_frame.zaxis * width
        plate_xaxis = btlx_ref_frame.xaxis
        plate_yaxis = -btlx_ref_frame.zaxis

        return Frame(plate_origin, plate_xaxis, plate_yaxis)

    def _infer_element_type(self, width, height, length, ratio_threshold=5.0):
        """Infers the element type (Beam or Plate) based on dimensional proportions.

        A beam is expected to have its length as the longest of the 3 dimensions
        with a relatively significant disproportion to the other two, which are
        relatively close in proportion.

        A plate is expected to have the thickness as the smallest of the 3
        dimensions with a relatively significant disproportion to the other two,
        which are relatively close in proportion.

        """
        dims = sorted([width, height, length])
        d_small, d_mid, d_large = dims

        ratio_mid_to_small = d_mid / d_small
        ratio_large_to_mid = d_large / d_mid

        # Plate-like: smallest dimension is thickness, significantly smaller than the other two, which are proportionally close.
        # e.g., 50x1000x2000 -> mid/small=20 > 5, large/mid=2 < 5 -> Plate
        is_plate_like = ratio_mid_to_small > ratio_threshold and ratio_large_to_mid < ratio_threshold

        # Beam-like: largest dimension is length, significantly larger than the other two, which are proportionally close.
        # e.g., 100x120x5000 -> mid/small=1.2 < 5, large/mid=41.6 > 5 -> Beam
        is_beam_like = ratio_mid_to_small < ratio_threshold and ratio_large_to_mid > ratio_threshold

        if is_plate_like and not is_beam_like:
            return "Plate"
        elif is_beam_like and not is_plate_like:
            return "Beam"
        else:
            # Default to Beam in ambiguous cases (e.g., cube, or both/neither conditions met)
            return "Beam"


def xml_to_contour(element):
    """Converts a Contour XML element to a Contour object.

    Parameters
    ----------
    element : :class:`~xml.etree.ElementTree.Element`
        The XML element representing the contour.

    Returns
    -------
    :class:`Contour`
        The Contour object.

    """
    # Parse attributes
    depth = float(element.attrib.get("Depth", 0))
    depth_bounded = element.attrib.get("DepthBounded", "no").lower() in ["yes", "true"]
    inclination_attr = element.attrib.get("Inclination", None)

    # Parse StartPoint
    start_point_elem = element.find("{*}StartPoint")
    if start_point_elem is None:
        raise ValueError("Contour element missing StartPoint")

    start_x = float(start_point_elem.attrib["X"])
    start_y = float(start_point_elem.attrib["Y"])
    start_z = float(start_point_elem.attrib["Z"])
    points = [[start_x, start_y, start_z]]

    # Parse Line elements
    inclinations = []
    for line_elem in element.findall("{*}Line"):
        end_point_elem = line_elem.find("{*}EndPoint")
        if end_point_elem is None:
            raise ValueError("Line element missing EndPoint")

        end_x = float(end_point_elem.attrib["X"])
        end_y = float(end_point_elem.attrib["Y"])
        end_z = float(end_point_elem.attrib["Z"])
        points.append([end_x, end_y, end_z])

        # Check for per-segment inclination
        line_inclination = line_elem.attrib.get("Inclination", None)
        if line_inclination is not None:
            inclinations.append(float(line_inclination))

    # Determine inclination format
    if inclination_attr is not None:
        # Single inclination for all segments
        inclination = [float(inclination_attr)] * (len(points) - 1)
    elif inclinations:
        # Per-segment inclination
        inclination = inclinations
    else:
        # No inclination specified
        inclination = [0.0] * (len(points) - 1)

    polyline = Polyline(points)
    return Contour(polyline, depth, depth_bounded=depth_bounded, inclination=inclination)


def xml_to_dual_contour(element):
    """Converts a DualContour XML element to a DualContour object.

    Parameters
    ----------
    element : :class:`~xml.etree.ElementTree.Element`
        The XML element representing the dual contour.

    Returns
    -------
    :class:`DualContour`
        The DualContour object.

    """
    # Parse PrincipalContour
    principal_elem = element.find("{*}PrincipalContour")
    if principal_elem is None:
        raise ValueError("DualContour element missing PrincipalContour")

    principal_points = []
    start_point_elem = principal_elem.find("{*}StartPoint")
    if start_point_elem is None:
        raise ValueError("PrincipalContour missing StartPoint")

    principal_points.append([float(start_point_elem.attrib["X"]), float(start_point_elem.attrib["Y"]), float(start_point_elem.attrib["Z"])])

    for line_elem in principal_elem.findall("{*}Line"):
        end_point_elem = line_elem.find("{*}EndPoint")
        if end_point_elem is None:
            raise ValueError("Line element missing EndPoint")
        principal_points.append([float(end_point_elem.attrib["X"]), float(end_point_elem.attrib["Y"]), float(end_point_elem.attrib["Z"])])

    # Parse AssociatedContour
    associated_elem = element.find("{*}AssociatedContour")
    if associated_elem is None:
        raise ValueError("DualContour element missing AssociatedContour")

    associated_points = []
    start_point_elem = associated_elem.find("{*}StartPoint")
    if start_point_elem is None:
        raise ValueError("AssociatedContour missing StartPoint")

    associated_points.append([float(start_point_elem.attrib["X"]), float(start_point_elem.attrib["Y"]), float(start_point_elem.attrib["Z"])])

    for line_elem in associated_elem.findall("{*}Line"):
        end_point_elem = line_elem.find("{*}EndPoint")
        if end_point_elem is None:
            raise ValueError("Line element missing EndPoint")
        associated_points.append([float(end_point_elem.attrib["X"]), float(end_point_elem.attrib["Y"]), float(end_point_elem.attrib["Z"])])

    principal_contour = Polyline(principal_points)
    associated_contour = Polyline(associated_points)
    return DualContour(principal_contour, associated_contour)


def xml_to_contour_or_dual(element):
    """Unified deserializer for Contour and DualContour elements.

    Inspects the XML element tag to determine whether to deserialize as
    Contour or DualContour. This handles FreeContour's polymorphic
    contour_param_object attribute.

    Parameters
    ----------
    element : :class:`~xml.etree.ElementTree.Element`
        The XML element representing either a Contour or DualContour.

    Returns
    -------
    :class:`Contour` or :class:`DualContour`
        The appropriate contour object based on the element tag.

    """
    tag_name = element.tag.split("}")[-1]  # Remove namespace
    if tag_name == "DualContour":
        return xml_to_dual_contour(element)
    else:  # "Contour"
        return xml_to_contour(element)


# Register deserializers for complex types
# Use unified deserializer for both Contour and DualContour to handle polymorphic FreeContour parameter
BTLxReader.register_type_deserializer("Contour", xml_to_contour_or_dual)
BTLxReader.register_type_deserializer("DualContour", xml_to_contour_or_dual)
