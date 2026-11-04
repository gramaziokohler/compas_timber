import xml.etree.ElementTree as ET
from collections import OrderedDict

from compas.data import Data
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import distance_point_plane
from compas.tolerance import TOL

from compas_timber.errors import BTLxParsingError
from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import is_polyline_clockwise

from .btlx import AlignmentType
from .btlx import AttributeSpec
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import BTLxWriter
from .btlx import Contour
from .btlx import DualContour
from .btlx import NurbsContour
from .btlx import ParametricProcessing
from .free_contour import FreeContour
from .free_contour import FreeContourParams


class CrampAngleRefType(object):
    """Enum for the direction the angle of a cramp is measured from.

    Attributes
    ----------
    SEGMENT : literal("segment")
        The segment of the contour.
    PART : literal("part")
        The X axis of the part.
    GRAIN : literal("grain")
        The grain direction of the part.
    """

    SEGMENT = "segment"
    PART = "part"
    GRAIN = "grain"


class SimpleContour(Data):
    """The path of a processing which follows a contour, with the attributes :class:`Contour` has no place for.

    The attributes a processing can use depend on its type, see its `ALLOWED_ATTRIBUTES`.

    Parameters
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The path, in the coordinates of the reference side. A single point stands for one nail, cramp or screw.
    nail_length : float, optional
        The length of the nails. Greater than 0.
    cramp_width : float, optional
        The width of the cramps. Greater than 0.
    screw_length : float, optional
        The length of the screws. Greater than 0.
    screw_diameter : float, optional
        The diameter of the screws.
    nail_spacing : float or list(float), optional
        The distance between the nails, cramps or screws along a segment.
        A list has one entry per point of `polyline`, the entry of a point is for the segment which ends in it. The first entry is not used.
    cramp_angle : float or list(float), optional
        The angle of the cramps. A list has one entry per point of `polyline`, as `nail_spacing`, and the first one is used by the start point.
    cramp_angle_ref : str or list(str), optional
        What `cramp_angle` is measured from, see :class:`CrampAngleRefType`. A list has one entry per point of `polyline`, as `cramp_angle`.

    """

    # shortcut: straight segments only, as with Contour, upgrade when arcs or NURBS are needed by a real file
    LENGTH_ATTRIBUTES = {"NailLength": "nail_length", "CrampWidth": "cramp_width", "ScrewLength": "screw_length", "ScrewDiameter": "screw_diameter"}
    POINT_ATTRIBUTES = {"NailSpacing": "nail_spacing", "CrampAngleRef": "cramp_angle_ref", "CrampAngle": "cramp_angle"}

    @property
    def __data__(self):
        data = {"polyline": self.polyline}
        for name in list(self.LENGTH_ATTRIBUTES.values()) + list(self.POINT_ATTRIBUTES.values()):
            data[name] = getattr(self, name)
        return data

    def __init__(self, polyline, nail_length=None, cramp_width=None, screw_length=None, screw_diameter=None, nail_spacing=None, cramp_angle=None, cramp_angle_ref=None):
        super(SimpleContour, self).__init__()
        self.polyline = polyline
        self.nail_length = nail_length
        self.cramp_width = cramp_width
        self.screw_length = screw_length
        self.screw_diameter = screw_diameter
        self.nail_spacing = self._per_point(nail_spacing)
        self.cramp_angle = self._per_point(cramp_angle)
        self.cramp_angle_ref = self._per_point(cramp_angle_ref)

        for name in ("nail_length", "cramp_width", "screw_length"):
            if getattr(self, name) is not None and getattr(self, name) <= 0.0:
                raise ValueError("{} must be greater than 0. Got: {}".format(name, getattr(self, name)))
        if screw_diameter is not None and not 0.0 <= screw_diameter <= 1000.0:
            raise ValueError("screw_diameter must be between 0.0 and 1000.0. Got: {}".format(screw_diameter))
        if any(value is not None and not 0.0 <= value <= 100000.0 for value in self.nail_spacing or []):
            raise ValueError("nail_spacing must be between 0.0 and 100000.0. Got: {}".format(nail_spacing))
        if any(value is not None and not -179.9 <= value <= 179.9 for value in self.cramp_angle or []):
            raise ValueError("cramp_angle must be between -179.9 and 179.9. Got: {}".format(cramp_angle))
        if any(value not in (None, CrampAngleRefType.SEGMENT, CrampAngleRefType.PART, CrampAngleRefType.GRAIN) for value in self.cramp_angle_ref or []):
            raise ValueError("cramp_angle_ref must be one of segment, part or grain. Got: {}".format(cramp_angle_ref))

    def _per_point(self, value):
        return [value] * len(self.polyline) if value is not None and not isinstance(value, list) else value

    def scale(self, factor):
        """Scale the path and the lengths of this contour.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        self.polyline.scale(factor)
        for name in self.LENGTH_ATTRIBUTES.values():
            if getattr(self, name) is not None:
                setattr(self, name, getattr(self, name) * factor)
        if self.nail_spacing:
            self.nail_spacing = [None if value is None else value * factor for value in self.nail_spacing]

    @classmethod
    def from_xml(cls, element):
        """Creates a contour from the XML element which holds it.

        Parameters
        ----------
        element : :class:`~xml.etree.ElementTree.Element`
            The element, a `Contour` or an `Aperture`.

        Returns
        -------
        :class:`SimpleContour`

        """
        if element.find("{*}Arc") is not None or element.find("{*}NURBS") is not None:
            raise BTLxParsingError("Contour with arc or NURBS segments is not supported.", processing_type="Contour")

        start_point = element.find("{*}StartPoint")
        lines = element.findall("{*}Line")
        points = [[float(point.attrib[axis]) for axis in "XYZ"] for point in [start_point] + [line.find("{*}EndPoint") for line in lines]]

        kwargs = {name: float(element.attrib[key]) for key, name in cls.LENGTH_ATTRIBUTES.items() if key in element.attrib}
        for key, name in cls.POINT_ATTRIBUTES.items():
            values = [node.attrib.get(key) for node in [start_point] + lines]
            if any(value is not None for value in values):
                kwargs[name] = values if key == "CrampAngleRef" else [None if value is None else float(value) for value in values]
        return cls(Polyline(points), **kwargs)


def _number(value):
    return "{:.{prec}f}".format(value, prec=BTLxWriter.POINT_PRECISION)


def simple_contour_to_xml(contour, tag="Contour"):
    """Converts a contour to an XML element.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The contour to be converted.
    tag : str, optional
        The tag of the element.

    Returns
    -------
    :class:`~xml.etree.ElementTree.Element`
        The element which represents the contour.

    """
    attributes = {key: _number(getattr(contour, name)) for key, name in contour.LENGTH_ATTRIBUTES.items() if getattr(contour, name) is not None}
    root = ET.Element(tag, attributes)
    for index, point in enumerate(contour.polyline):
        attributes = {}
        for key, name in contour.POINT_ATTRIBUTES.items():
            value = getattr(contour, name)[index] if getattr(contour, name) else None
            if value is not None and not (key == "NailSpacing" and index == 0):  # a start point ends no segment
                attributes[key] = value if isinstance(value, str) else _number(value)

        coordinates = {axis: _number(value) for axis, value in zip("XYZ", point)}
        if index == 0:
            ET.SubElement(root, "StartPoint", dict(coordinates, **attributes))
        else:
            ET.SubElement(ET.SubElement(root, "Line", attributes), "EndPoint", coordinates)
    return root


BTLxWriter.register_type_serializer(SimpleContour.__name__, simple_contour_to_xml)


class ContourProcessingParams(BTLxProcessingParams):
    """Writes the entries of `ATTRIBUTE_MAP` which are not child elements as attributes of the processing element."""

    @property
    def header_attributes(self):
        result = super(ContourProcessingParams, self).header_attributes
        for name, value in super(ContourProcessingParams, self).as_dict().items():
            if name not in self._instance.CHILD_ELEMENTS:
                result[name] = value
        return result

    def as_dict(self):
        params = super(ContourProcessingParams, self).as_dict()
        return OrderedDict((name, value) for name, value in params.items() if name in self._instance.CHILD_ELEMENTS)


class ContourProcessing(ParametricProcessing):
    """Base class for the processings which are defined by a :class:`SimpleContour`.

    The BTLx attributes of the processing element are declared in `ATTRIBUTE_MAP` as well, which gives them
    the validation, data and scaling of :class:`ParametricProcessing`. Only `CHILD_ELEMENTS` are written as elements.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The contour.

    Attributes
    ----------
    ALLOWED_ATTRIBUTES : tuple(str)
        The attributes of a :class:`SimpleContour` which the BTLx schema allows for this processing.
    MIN_POINTS : int
        The minimum number of points of the contour.

    """

    ATTRIBUTE_MAP = {"Contour": AttributeSpec("contour", SimpleContour)}
    CHILD_ELEMENTS = ("Contour", "Apertures")
    ALLOWED_ATTRIBUTES = ()
    MIN_POINTS = 2

    def __init_subclass__(cls, **kwargs):
        super(ContourProcessing, cls).__init_subclass__(**kwargs)
        cls.HEADER_ATTRIBUTE_MAP = dict(BTLxProcessing.HEADER_ATTRIBUTE_MAP)
        for name, spec in cls.ATTRIBUTE_MAP.items():
            if name not in cls.CHILD_ELEMENTS:
                cls.HEADER_ATTRIBUTE_MAP[name] = (spec.python_name, spec.type)

    def __init__(self, **kwargs):
        super(ContourProcessing, self).__init__(**kwargs)
        if not isinstance(self.contour, SimpleContour):
            raise ValueError("contour must be an instance of SimpleContour. Got: {}".format(self.contour))
        if len(self.contour.polyline) < self.MIN_POINTS:
            raise ValueError("The contour of {} needs at least {} points.".format(self.PROCESSING_NAME, self.MIN_POINTS))
        names = list(SimpleContour.LENGTH_ATTRIBUTES.values()) + list(SimpleContour.POINT_ATTRIBUTES.values())
        invalid = [name for name in names if getattr(self.contour, name) is not None and name not in self.ALLOWED_ATTRIBUTES]
        if invalid:
            raise ValueError("The contour of {} cannot have: {}".format(self.PROCESSING_NAME, invalid))

    @property
    def params(self):
        return ContourProcessingParams(self)

    def scale(self, factor):
        """Scale the lengths of this processing and of its contour.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        super(ContourProcessing, self).scale(factor)
        self.contour.scale(factor)

    @classmethod
    def from_polyline_and_element(cls, polyline, element, ref_side_index=None, **kwargs):
        """Construct this processing from a polyline and an element.

        Parameters
        ----------
        polyline : :class:`~compas.geometry.Polyline`
            The contour, in model coordinates.
        element : :class:`~compas_timber.base.TimberElement`
            The element.
        ref_side_index : int, optional
            The reference side. By default the one all points of `polyline` lie on.
        **kwargs : dict, optional
            The attributes of the contour (see `ALLOWED_ATTRIBUTES`), and the keyword arguments of this processing.

        Returns
        -------
        :class:`ContourProcessing`

        """
        if ref_side_index is None:
            ref_side_index = cls._ref_side_index_of_polyline(polyline, element)
        contour_attributes = {name: kwargs.pop(name) for name in cls.ALLOWED_ATTRIBUTES if name in kwargs}
        contour = SimpleContour(polyline.transformed(Transformation.from_frame(element.ref_sides[ref_side_index]).inverse()), **contour_attributes)
        return cls(contour=contour, ref_side_index=ref_side_index, **kwargs)

    @classmethod
    def from_shapes_and_element(cls, polyline, element, **kwargs):
        """Construct this processing from a polyline and an element, see :meth:`from_polyline_and_element`."""
        return cls.from_polyline_and_element(polyline, element, **kwargs)

    @staticmethod
    def _ref_side_index_of_polyline(polyline, element):
        for index, ref_side in enumerate(element.ref_sides):
            if all(TOL.is_zero(distance_point_plane(point, Plane.from_frame(ref_side)), tol=1e-6) for point in polyline):
                return index
        raise ValueError("The polyline does not lay on one of the reference sides of the element.")


class _ToolContourMixin(object):
    """Adds to :meth:`FreeContour.apply` what the figures say about a saw or mill contour and what is not in :class:`Contour`.

    This is not a :class:`FreeContour`, because a subclass would inherit its processing name and replace it in the reader.
    """

    def apply(self, geometry, element):
        """Apply the feature to the element's geometry.

        A closed contour with `counter_sink` removes the material inside of it, without it the material outside of it.

        Parameters
        ----------
        geometry : :class:`~compas_brep.Brep`
            The element's geometry, in the element's local coordinates.
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If there is no volume, which is the case for an open contour.

        Returns
        -------
        :class:`~compas_brep.Brep`
            The resulting geometry.

        """
        # shortcut: an open contour fails, the groove it leaves depends on the width of the tool, which BTLx does not hold. Upgrade with a tool width.
        # shortcut: outside of a contour which is not through, everything is removed instead of a groove of the width of the tool, as with FreeContour. Same upgrade.
        processing = self
        if isinstance(self.contour_param_object, Contour) and not self.contour_param_object.depth_bounded:
            # the effective depth reaches the opposite side, whatever the depth in the file is
            processing = self.copy()
            is_end_side = self.ref_side_index in (4, 5)
            processing.contour_param_object.depth = element.blank_length if is_end_side else element.get_dimensions_relative_to_side(self.ref_side_index)[1]
        try:
            return super(_ToolContourMixin, processing).apply(geometry, element)
        except Exception as ex:  # to_brep() raises for a contour which gives no solid, which would otherwise end the computation of the geometry
            raise FeatureApplicationError(self.contour_param_object, geometry, "Failed to apply the {}: {}".format(self.PROCESSING_NAME, ex))


class SawContourParams(FreeContourParams):
    """Leaves out the attribute `SawContourType` does not have."""

    @property
    def header_attributes(self):
        result = super(SawContourParams, self).header_attributes
        del result["CounterSink"]
        return result


class SawContour(_ToolContourMixin, FreeContour):
    """Represents a contour which is cut with a saw.

    It has the alternative constructors of :class:`FreeContour`.

    Parameters
    ----------
    contour_param_object : :class:`~compas_timber.fabrication.Contour`, :class:`~compas_timber.fabrication.DualContour` or :class:`~compas_timber.fabrication.NurbsContour`
        The contour. Its depth is measured from the contour along -Z of the reference side, and is only used if it is depth bounded.
        Otherwise the cut goes through. An inclination tilts the cut around a segment.
    tool_id : int, optional
        The tool ID for the processing.
    counter_sink : bool, optional
        True if the material inside of a closed contour is removed. It is not written to BTLx, as this type has no such attribute:
        by default it follows from the tool being on the side of the removed material.
    tool_position : :class:`~compas_timber.fabrication.AlignmentType`, optional
        The side of the contour the tool is on, in the direction of the contour, seen from outside of the reference side. Left, center or right.
    depth_bounded : bool, optional
        See :class:`FreeContour`.

    """

    PROCESSING_NAME = "SawContour"  # type: ignore

    def __init__(self, contour_param_object, tool_id=0, counter_sink=None, tool_position=AlignmentType.LEFT, depth_bounded=True, **kwargs):
        if counter_sink is None:
            if isinstance(contour_param_object, NurbsContour):
                polyline = contour_param_object.to_contour().polyline
            elif isinstance(contour_param_object, DualContour):
                polyline = contour_param_object.principal_contour
            else:
                polyline = contour_param_object.polyline
            counter_sink = tool_position == (AlignmentType.RIGHT if is_polyline_clockwise(polyline, Vector.Zaxis()) else AlignmentType.LEFT)
        super(SawContour, self).__init__(contour_param_object, tool_id, counter_sink, tool_position, depth_bounded, **kwargs)

    @property
    def params(self):
        return SawContourParams(self)


class MillContour(_ToolContourMixin, FreeContour):
    """Represents a contour which is cut with a milling tool.

    It has the alternative constructors of :class:`FreeContour`.

    Parameters
    ----------
    contour_param_object : :class:`~compas_timber.fabrication.Contour` or :class:`~compas_timber.fabrication.DualContour`
        The contour. See :class:`SawContour`.
    tool_id : int, optional
        The tool ID for the processing.
    counter_sink : bool, optional
        True if the material inside of a closed contour is removed, False if the tool only follows the contour.
    tool_position : :class:`~compas_timber.fabrication.AlignmentType`, optional
        The side of the contour the tool is on. See :class:`SawContour`.
    depth_bounded : bool, optional
        See :class:`FreeContour`.

    """

    PROCESSING_NAME = "MillContour"  # type: ignore


class NailContour(ContourProcessing):
    """Represents nails along a contour. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The path of the nails, with `nail_length` and `nail_spacing`. A single point is one nail.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "NailContour"  # type: ignore
    ALLOWED_ATTRIBUTES = ("nail_length", "nail_spacing")
    MIN_POINTS = 1


class CrampContour(ContourProcessing):
    """Represents cramps along a contour. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The path of the cramps, with `nail_length`, `cramp_width`, `nail_spacing`, `cramp_angle` and `cramp_angle_ref`. A single point is one cramp.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "CrampContour"  # type: ignore
    ALLOWED_ATTRIBUTES = ("nail_length", "cramp_width", "nail_spacing", "cramp_angle", "cramp_angle_ref")
    MIN_POINTS = 1


class ScrewContour(ContourProcessing):
    """Represents screws along a contour. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The path of the screws, with `screw_length`, `screw_diameter` and `nail_spacing`. A single point is one screw.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "ScrewContour"  # type: ignore
    ALLOWED_ATTRIBUTES = ("screw_length", "screw_diameter", "nail_spacing")
    MIN_POINTS = 1


class PenContour(ContourProcessing):
    """Represents a contour drawn with a pen. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The path of the pen.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "PenContour"  # type: ignore
