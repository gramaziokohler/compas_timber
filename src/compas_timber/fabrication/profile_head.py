import math
import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Point

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .profile_front import ArcShapeType
from .profile_front import closed_towards_head
from .profile_front import element_size
from .profile_front import extruded_volume
from .profile_front import polyline_curves
from .profile_front import segment_curves


class ProfileArc(Data):
    """One step of a :class:`ProfileHead`: a displacement, a quarter arc or segment, and a lap, climbing towards the reference side.

    Parameters
    ----------
    radius : float, optional
        Radius of a QuarterArc. Used unless one of the parameters of a Segment is given.
    length : float, optional
        Length of a Segment along X. Defaults to 50.0 for a Segment.
    height : float, optional
        Height of a Segment, along the normal of the reference side. Defaults to 50.0 for a Segment.
    camber : float, optional
        Height of the arc of a Segment above its chord. Defaults to 50.0 for a Segment.
    arc_shape : str, optional
        `convex` if the arc bulges towards the reference side, `concave` if it bulges into the material.
    lap_length : float, optional
        Length of the flat following the arc, along X.
    lap_height : float, optional
        Height of the riser following the flat.
    displacement : float, optional
        Length of the flat before the arc, along X.

    Attributes
    ----------
    tag : str
        The name of the BTLx element. Set by the :class:`ProfileHead` holding this arc, as the writer only gives serializers the value.

    """

    tag = "Arc1"

    def __init__(self, radius=50.0, length=None, height=None, camber=None, arc_shape=ArcShapeType.CONVEX, lap_length=10.0, lap_height=10.0, displacement=10.0):
        super(ProfileArc, self).__init__()
        if arc_shape not in (ArcShapeType.CONVEX, ArcShapeType.CONCAVE):
            raise ValueError("arc_shape must be convex or concave. Got: {}".format(arc_shape))
        if length is not None or height is not None or camber is not None:
            radius = None
            length, height, camber = [50.0 if value is None else value for value in (length, height, camber)]
        for value in (radius, length, height, camber, lap_length, lap_height, displacement):
            if value is not None and not 0.0 <= value <= 1000.0:
                raise ValueError("The dimensions of a profile arc must be between 0.0 and 1000.0. Got: {}".format(value))
        self.radius = radius
        self.length = length
        self.height = height
        self.camber = camber
        self.arc_shape = arc_shape
        self.lap_length = lap_length
        self.lap_height = lap_height
        self.displacement = displacement

    @property
    def __data__(self):
        return {
            "radius": self.radius,
            "length": self.length,
            "height": self.height,
            "camber": self.camber,
            "arc_shape": self.arc_shape,
            "lap_length": self.lap_length,
            "lap_height": self.lap_height,
            "displacement": self.displacement,
        }

    @property
    def arc_length(self):
        """The extent of the arc along X."""
        return self.length if self.radius is None else self.radius

    @property
    def arc_height(self):
        """The extent of the arc along the normal of the reference side."""
        return self.height if self.radius is None else self.radius

    @property
    def rise(self):
        """The distance this step climbs towards the reference side."""
        return self.arc_height + self.lap_height

    @property
    def signed_camber(self):
        """The height of the arc above its chord, positive to the left of the direction of travel."""
        camber = self.camber if self.radius is None else self.radius * (1.0 - math.sqrt(0.5))
        return camber if self.arc_shape == ArcShapeType.CONVEX else -camber

    def scale(self, factor):
        """Scale the lengths of this arc.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        for name in ("radius", "length", "height", "camber", "lap_length", "lap_height", "displacement"):
            if getattr(self, name) is not None:
                setattr(self, name, getattr(self, name) * factor)

    @classmethod
    def from_xml(cls, element):
        """Creates a profile arc from its BTLx element.

        Parameters
        ----------
        element : :class:`~xml.etree.ElementTree.Element`
            The Arc1 or Arc2 element.

        Returns
        -------
        :class:`ProfileArc`

        """
        kwargs = {
            "arc_shape": element.get("ArcShape", ArcShapeType.CONVEX),
            "lap_length": float(element.get("LapLength", 10.0)),
            "lap_height": float(element.get("LapHeight", 10.0)),
            "displacement": float(element.get("Displacement", 10.0)),
        }
        shape = element[0]
        if shape.tag.split("}")[-1] == "QuarterArc":
            return cls(radius=float(shape.get("Radius", 50.0)), **kwargs)
        return cls(length=float(shape.get("Length", 50.0)), height=float(shape.get("Height", 50.0)), camber=float(shape.get("Camber", 50.0)), **kwargs)


def profile_arc_to_xml(arc):
    """Creates the Arc1 or Arc2 element of a :class:`ProfileArc`."""

    def formatted(value):
        return "{:.3f}".format(value)

    element = ET.Element(
        arc.tag,
        {"ArcShape": arc.arc_shape, "LapLength": formatted(arc.lap_length), "LapHeight": formatted(arc.lap_height), "Displacement": formatted(arc.displacement)},
    )
    if arc.radius is None:
        ET.SubElement(element, "Segment", {"Length": formatted(arc.length), "Height": formatted(arc.height), "Camber": formatted(arc.camber)})
    else:
        ET.SubElement(element, "QuarterArc", {"Radius": formatted(arc.radius)})
    return element


BTLxWriter.register_type_serializer(ProfileArc.__name__, profile_arc_to_xml)


class ProfileHead(ParametricProcessing):
    """Represents a Profile Head feature to be made on a beam: a staircase of one or two arcs, extruded across the reference side.

    The profile lies in the plane of the X-axis and the normal of the reference side, and is cut through the whole element.
    Starting with a wall through the element at `start_x`, it climbs by a lap and its arcs, away from the end the orientation names, up to the reference side.
    The depth of its start therefore follows from the steps. Everything between the profile and that end of the element is removed.

    Parameters
    ----------
    orientation : str
        The end of the element the profile faces. One of :class:`~compas_timber.fabrication.OrientationType`.
    start_x : float
        Distance from the start of the reference side to the start of the profile, along X.
    arc1 : :class:`ProfileArc`, optional
        The step of the profile following the lap. Defaults to a :class:`ProfileArc` with default parameters.
    arc2 : :class:`ProfileArc`, optional
        The optional step following `arc1`.
    lap_length : float
        Length of the flat at the start of the profile, along X.
    lap_height : float
        Height of the riser following the flat.

    """

    PROCESSING_NAME = "ProfileHead"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Arc1": AttributeSpec("arc1", ProfileArc),
        "Arc2": AttributeSpec("arc2", ProfileArc),
        "LapLength": AttributeSpec("lap_length", float, 10.0, (0.0, 1000.0), scales=True),
        "LapHeight": AttributeSpec("lap_height", float, 10.0, (0.0, 1000.0), scales=True),
    }

    def __init__(self, **kwargs):
        kwargs["arc1"] = kwargs.get("arc1") or ProfileArc()
        super(ProfileHead, self).__init__(**kwargs)

    @property
    def arc1(self):
        return self._arc1

    @arc1.setter
    def arc1(self, value):
        self._arc1 = value.copy()  # the same arc may be given as arc2, which gets another tag
        self._arc1.tag = "Arc1"

    @property
    def arc2(self):
        return self._arc2

    @arc2.setter
    def arc2(self, value):
        self._arc2 = value and value.copy()
        if value:
            self._arc2.tag = "Arc2"

    def scale(self, factor):
        """Scale the length parameters of this processing.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        super(ProfileHead, self).scale(factor)
        self.arc1.scale(factor)
        if self.arc2:
            self.arc2.scale(factor)

    def volumes_from_params_and_element(self, element):
        """The volume above the profile and towards the end of the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        arcs = [arc for arc in (self.arc1, self.arc2) if arc]
        x, z = self.lap_length, -sum(arc.rise for arc in arcs)
        start_z = z - self.lap_height
        curves = polyline_curves([Point(0.0, 0.0, start_z - element_size(element)), Point(0.0, 0.0, start_z), Point(x, 0.0, start_z), Point(x, 0.0, z)])
        for arc in arcs:
            arc_start = Point(x + arc.displacement, 0.0, z)
            arc_end = Point(arc_start.x + arc.arc_length, 0.0, z + arc.arc_height)
            x, z = arc_end.x + arc.lap_length, arc_end.z + arc.lap_height
            curves += polyline_curves([Point(arc_start.x - arc.displacement, 0.0, arc_start.z), arc_start])
            curves += segment_curves(arc_start, arc_end, arc.signed_camber)
            curves += polyline_curves([arc_end, Point(x, 0.0, arc_end.z), Point(x, 0.0, z)])
        return [extruded_volume(closed_towards_head(curves, self.start_x, element), self.start_x, element, self.ref_side_index, self.orientation)]
