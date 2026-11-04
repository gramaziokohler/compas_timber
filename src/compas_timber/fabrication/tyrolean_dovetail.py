import math
import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Polyhedron
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .btlx import EdgePositionType
from .btlx import OrientationType
from .dovetail import LENGTH_POS
from .dovetail import WIDTH
from .dovetail import WIDTH_N
from .dovetail import CornerLock
from .dovetail import LapExitType
from .dovetail import ProcessSideType
from .dovetail import point_mapper
from .dovetail import prism

CIRCLE_SEGMENTS = 48  # shortcut: the Frosch's cones are faceted, upgrade with true cones if their surface must be exact


class TyroleanDovetailShapeType(object):
    """Enum for the shape of a :class:`TyroleanDovetail`.

    Attributes
    ----------
    ANGULAR : literal("angular")
        The faces of the tail slope both along the element and along the shoulder.
    STRAIGHT : literal("straight")
        The faces of the tail slope along the element only.
    """

    ANGULAR = "angular"
    STRAIGHT = "straight"


class _LockProfile(Data):
    """Base class of the two optional details of a :class:`TyroleanDovetail`, which hold two lengths."""

    TAGS = ()

    def __init__(self, first, second):
        super(_LockProfile, self).__init__()
        if not all(WIDTH[0] <= value <= WIDTH[1] for value in (first, second)):
            raise ValueError("{} must be between {} and {}.".format(" and ".join(self.TAGS), *WIDTH))
        self._values = [first, second]

    def scale(self, factor):
        """Scale the lengths by a given factor."""
        self._values = [value * factor for value in self._values]

    @classmethod
    def from_xml(cls, element):
        """Creates an instance from its XML element."""
        return cls(*[float(element.find("{*}" + tag).text) for tag in cls.TAGS])


class Frosch(_LockProfile):
    """The "Frosch" of a :class:`TyroleanDovetail`: a circular bulge on the inner side of the tail, which locks in pockets in the corners of the shoulder.

    Parameters
    ----------
    width : float
        How far the bulge stops short of the shoulder and the pockets stop short of the lap. 0.0 < width < 50000.0.
    depth : float
        How far the bulge stands out of the tail and the pockets go into the shoulder. 0.0 < depth < 50000.0.

    """

    TAGS = ("Width", "Depth")

    @property
    def __data__(self):
        return {"width": self.width, "depth": self.depth}

    def __init__(self, width, depth):
        super(Frosch, self).__init__(width, depth)

    @property
    def width(self):
        return self._values[0]

    @property
    def depth(self):
        return self._values[1]


class Klingschrot(_LockProfile):
    """The "Klingschrot" of a :class:`TyroleanDovetail`: the faces of the tail are cut with a tool with a curved profile.

    Parameters
    ----------
    radius : float
        Radius of the profile of the tool. 0.0 < radius < 50000.0.
    arc_length : float
        Length of the profile of the tool. 0.0 < arc_length < 50000.0.

    """

    TAGS = ("Radius", "ArcLength")

    @property
    def __data__(self):
        return {"radius": self.radius, "arc_length": self.arc_length}

    def __init__(self, radius, arc_length):
        super(Klingschrot, self).__init__(radius, arc_length)

    @property
    def radius(self):
        return self._values[0]

    @property
    def arc_length(self):
        return self._values[1]


def _lock_profile_to_xml(profile):
    root = ET.Element(type(profile).__name__)
    for tag, value in zip(profile.TAGS, profile._values):
        ET.SubElement(root, tag).text = "{:.{prec}f}".format(value, prec=BTLxWriter.POINT_PRECISION)
    return root


BTLxWriter.register_type_serializer(Frosch.__name__, _lock_profile_to_xml)
BTLxWriter.register_type_serializer(Klingschrot.__name__, _lock_profile_to_xml)


class TyroleanDovetail(CornerLock):
    """Represents a TyroleanDovetail feature, the "Tiroler Schloss" corner lock of a log house.

    The tail is a parallelogram in the plan of the reference side: between the line through `start_x` on the reference edge at `angle` to this edge and the shoulder at
    distance `length` from it. Its two faces are symmetrical to `start_depth`. They move apart by `slope` towards `start_x` and towards the lap, so that the tail locks in
    both directions.

    Parameters
    ----------
    orientation : str
        Which end of the element is processed. :attr:`OrientationType.START` or :attr:`OrientationType.END`.
    cut_off : bool
        True if the element is trimmed at the end of the tail. Otherwise the material behind the tail remains.
    start_x : float
        Distance from the start of the element to the end of the tail, on the reference edge. -100000.0 < start_x < 100000.0.
    start_y : float
        Width of the lap, measured from the edge of the element which is opposite of the tail. 0.0 < start_y < 50000.0.
    start_depth : float
        Depth, from the reference side, of the plane of symmetry of the tail. -50000.0 < start_depth < 50000.0.
    angle : float, optional
        Angle between the reference edge and the shoulder, inside of the tail, in degrees. 0.1 < angle < 179.9.
    slope : float, optional
        Inclination of the faces of the tail, in degrees. 0.0 < slope < 45.0.
    length : float
        Length of the tail, perpendicular to the shoulder. 0.0 < length < 50000.0.
    rebate_length : float
        Length of the step, perpendicular to the shoulder, if `lap_exit` is :attr:`LapExitType.REBATE`. 0.0 < rebate_length < 50000.0.
    height : float
        Distance of the faces to `start_depth`, at the corner of the shoulder and the lap. 0.0 < height < 50000.0.
    lap_position : str
        The edge of the element where the tail is. :attr:`EdgePositionType.REFEDGE` or :attr:`EdgePositionType.OPPEDGE`.
    lap_exit : str
        Shape of the transition from the lap to the part. One of :class:`LapExitType`.
    shape : str
        Shape of the faces of the tail. One of :class:`TyroleanDovetailShapeType`.
    process_side : str
        Which of the faces are cut. One of :class:`ProcessSideType`.
    frosch : :class:`Frosch`, optional
        Adds a Frosch to the tail. Excludes `klingschrot`.
    klingschrot : :class:`Klingschrot`, optional
        Cuts the faces with a Klingschrot tool. Excludes `frosch`.

    """

    PROCESSING_NAME = "TyroleanDovetail"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "CutOff": AttributeSpec("cut_off", bool, False),
        "StartX": AttributeSpec("start_x", float, 0.0, LENGTH_POS, scales=True),
        "StartY": AttributeSpec("start_y", float, 30.0, WIDTH, scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 50.0, WIDTH_N, scales=True),
        "Angle": AttributeSpec("angle", float, None, (0.1, 179.9)),
        "Slope": AttributeSpec("slope", float, None, (0.0, 45.0)),
        "Length": AttributeSpec("length", float, 150.0, WIDTH, scales=True),
        "RebateLength": AttributeSpec("rebate_length", float, 10.0, WIDTH, scales=True),
        "Height": AttributeSpec("height", float, 60.0, WIDTH, scales=True),
        "LapPosition": AttributeSpec("lap_position", str, EdgePositionType.REFEDGE, choices=(EdgePositionType.REFEDGE, EdgePositionType.OPPEDGE)),
        "LapExit": AttributeSpec("lap_exit", str, LapExitType.MITRE, choices=(LapExitType.NONE, LapExitType.MITRE, LapExitType.REBATE)),
        "Shape": AttributeSpec("shape", str, TyroleanDovetailShapeType.ANGULAR, choices=(TyroleanDovetailShapeType.ANGULAR, TyroleanDovetailShapeType.STRAIGHT)),
        "ProcessSide": AttributeSpec("process_side", str, ProcessSideType.BOTH, choices=(ProcessSideType.BOTH, ProcessSideType.REFSIDE, ProcessSideType.OPPSIDE)),
        "Frosch": AttributeSpec("frosch", Frosch),
        "Klingschrot": AttributeSpec("klingschrot", Klingschrot),
    }

    def __init__(self, **kwargs):
        super(TyroleanDovetail, self).__init__(**kwargs)
        if self.frosch and self.klingschrot:
            raise ValueError("A TyroleanDovetail has either a Frosch or a Klingschrot, not both.")

    def scale(self, factor):
        """Scale the length parameters of this processing.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        super(TyroleanDovetail, self).scale(factor)
        for profile in (self.frosch, self.klingschrot):
            if profile:
                profile.scale(factor)

    def volumes_from_params_and_element(self, element):
        """The volumes this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If `angle` or `slope` is not set.

        Returns
        -------
        list(:class:`~compas_brep.Brep` or :class:`~compas.geometry.Polyhedron`)
            The volumes, in model coordinates.

        """
        if self.angle is None or self.slope is None:
            raise ValueError("The angle and the slope of the TyroleanDovetail must be set.")
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        to_model = point_mapper(self, element, self._mirrored)
        margin = width + height + self.length + self.height + abs(self.start_depth)
        inner = width - self.start_y
        outer = width + margin

        # along = origin - across * lean is the line of the tail's end, the shoulder is parallel to it
        sine, cosine = math.sin(math.radians(self.angle)), math.cos(math.radians(self.angle))
        lean = -cosine / sine if self._mirrored else cosine / sine
        origin = width * lean if self._mirrored else 0.0
        offset = self.length / sine

        def end(across):
            return origin - across * lean

        def shoulder(across):
            return end(across) + offset

        def start(across):
            return end(across) - margin if self.cut_off else end(across)

        corner = shoulder(inner)
        # The figures only show tails as long as they are wide, where `height` fits several points. It is taken at the corner of the shoulder and the lap, the only
        # one which fits both lap positions, and `slope` along the edges of the parallelogram. No figure shows the shape: straight is read as without the slope along the shoulder.
        cross = 0.0 if self.shape == TyroleanDovetailShapeType.STRAIGHT else (1.0 - sine * lean) / sine
        tangent = math.tan(math.radians(self.slope))

        def upper_face(along, across):
            return self.start_depth - self.height + tangent * (along - corner + (inner - across) * cross)

        def lower_face(along, across):
            return 2.0 * self.start_depth - upper_face(along, across)

        if self.frosch and self.frosch.width >= min(corner - end(inner), inner):
            raise ValueError("The width of the Frosch must be smaller than the length and the width of the tail.")

        volumes = []
        if self.cut_off:
            far = abs(self.start_x) + element.blank_length + margin + abs(lean) * outer
            plan = [(end(-margin), -margin), (end(outer), outer), (end(outer) - far, outer), (end(-margin) - far, -margin)]
            volumes.append(prism([to_model(a, b, -margin) for a, b in plan], [to_model(a, b, height + margin) for a, b in plan]))

        plan = self._lap_outline(corner, inner, outer, start(inner), start(outer), self.angle)
        lap = prism([to_model(a, b, -margin) for a, b in plan], [to_model(a, b, height + margin) for a, b in plan])
        if self.frosch:
            volumes.extend(Brep.from_boolean_difference(lap, self._bulge(to_model, end(inner), corner, inner, upper_face)))
        else:
            volumes.append(lap)

        # shortcut: a Klingschrot's faces are curved in both directions, here they stay planar, upgrade with a swept tool profile
        plan = [(start(-margin), -margin), (shoulder(-margin), -margin), (shoulder(outer), outer), (start(outer), outer)]
        if self.process_side != ProcessSideType.OPPSIDE:
            top = min(min(upper_face(a, b) for a, b in plan), 0.0) - margin
            volumes.append(self._wedge(to_model, plan, top, upper_face))
            if self.frosch:
                volumes.append(self._pocket(to_model, shoulder, inner, 0.0, upper_face(shoulder(0.0), 0.0)))
        if self.process_side != ProcessSideType.REFSIDE:
            bottom = max(max(lower_face(a, b) for a, b in plan), height) + margin
            volumes.append(self._wedge(to_model, plan, bottom, lower_face))
            if self.frosch:
                volumes.append(self._pocket(to_model, shoulder, inner, height, lower_face(shoulder(0.0), 0.0)))
        return volumes

    @staticmethod
    def _wedge(to_model, plan, lid, face):
        vertices = [to_model(a, b, lid) for a, b in plan] + [to_model(a, b, face(a, b)) for a, b in plan]
        return Polyhedron(vertices=vertices, faces=[[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])

    def _bulge(self, to_model, end, corner, inner, upper_face):
        # measured on the figure: the arc runs through the corners of the tail's end and stops frosch.width short of the shoulder. The top plane cuts it flush with the tail.
        rise = (corner - self.frosch.width) - end
        half_chord = self.start_depth - upper_face(end, inner)
        radius = (rise**2 + half_chord**2) / (2.0 * rise)
        center = end + rise - radius

        def circle(across):
            growth = radius + (across - inner) * math.tan(math.radians(self.slope))
            return [
                to_model(center + growth * math.cos(angle), across, self.start_depth + growth * math.sin(angle))
                for angle in (2.0 * math.pi * i / CIRCLE_SEGMENTS for i in range(CIRCLE_SEGMENTS))
            ]

        return prism(circle(inner - self.frosch.depth), circle(inner + self.frosch.depth))

    def _pocket(self, to_model, shoulder, inner, side_depth, face_depth):
        # measured on the figure: the arc is centered on the element's side, runs through the outer corner of the tail and stops frosch.width short of the lap
        reach = inner - self.frosch.width
        rise = abs(face_depth - side_depth)
        center = (reach**2 - rise**2) / (2.0 * reach)
        radius = reach - center

        def circle(deeper):
            growth = radius + deeper * math.tan(math.radians(self.slope))
            points = []
            for i in range(CIRCLE_SEGMENTS):
                across = center + growth * math.cos(2.0 * math.pi * i / CIRCLE_SEGMENTS)
                points.append(to_model(shoulder(across) + deeper, across, side_depth + growth * math.sin(2.0 * math.pi * i / CIRCLE_SEGMENTS)))
            return points

        return prism(circle(0.0), circle(self.frosch.depth))
