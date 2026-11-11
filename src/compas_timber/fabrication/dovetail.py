import math

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector

from compas_timber.geometry import brep_from_outlines

from .btlx import AttributeSpec
from .btlx import EdgePositionType
from .btlx import OrientationType
from .btlx import ParametricProcessing

LENGTH_POS = (-100000.0, 100000.0)
WIDTH = (0.0, 50000.0)
WIDTH_N = (-50000.0, 50000.0)


class LapExitType(object):
    """Enum for the shape of the exit of a lap.

    Attributes
    ----------
    NONE : literal("none")
        The shoulder continues straight to the edge of the element.
    MITRE : literal("mitre")
        The exit bisects the corner between the lap and the shoulder.
    REBATE : literal("rebate")
        The exit is a step, parallel to the shoulder.
    """

    NONE = "none"
    MITRE = "mitre"
    REBATE = "rebate"


class ProcessSideType(object):
    """Enum for the sides of the element which are processed.

    Attributes
    ----------
    BOTH : literal("both")
        Both the reference side and the opposite side are processed.
    REFSIDE : literal("refside")
        Only the reference side is processed.
    OPPSIDE : literal("oppside")
        Only the side opposite of the reference side is processed.
    """

    BOTH = "both"
    REFSIDE = "refside"
    OPPSIDE = "oppside"


class DovetailShapeType(object):
    """Enum for the shape of a :class:`Dovetail`.

    Attributes
    ----------
    EUROPEAN : literal("european")
        The sloped faces end in a hook, perpendicular to them.
    AMERICAN : literal("american")
        The sloped faces run through, without a hook.
    """

    EUROPEAN = "european"
    AMERICAN = "american"


def point_mapper(processing, element, mirror_y=False):
    """Returns a function mapping (along, across, depth) to a point in model coordinates.

    `along` is measured from `start_x` towards the part which remains, whatever the orientation.
    `across` is the y coordinate of the reference side, or its distance to the opposite edge if `mirror_y`.
    `depth` is measured from the reference side into the element.

    """
    ref_side = element.ref_sides[processing.ref_side_index]
    width = element.get_dimensions_relative_to_side(processing.ref_side_index)[0]
    sign = 1.0 if processing.orientation == OrientationType.START else -1.0

    def to_model(along, across, depth):
        return ref_side.to_world_coordinates(Point(processing.start_x + sign * along, width - across if mirror_y else across, -depth))

    return to_model


def prism(start_points, end_points):
    """Returns the solid between two parallel outlines. The outlines are open lists of the same number of points."""
    outlines = [Polyline(points + points[:1]) for points in (start_points, end_points)]
    return brep_from_outlines(outlines[0], outlines[1], normal=Vector.from_start_end(start_points[0], end_points[0]))


class CornerLock(ParametricProcessing):
    """Base class of the log house corner locks :class:`Dovetail` and :class:`TyroleanDovetail`.

    Both are a tail of length `length` between `start_x` and a shoulder, which leaves a lap of width `start_y` on one side of the tail.

    """

    @property
    def _mirrored(self):
        return self.lap_position == EdgePositionType.OPPEDGE

    def _lap_outline(self, corner, inner, outer, start_inner, start_outer, angle=90.0):
        """The (along, across) outline of the lap, which ends in the exit behind the inner corner of the shoulder.

        `corner` is the `along` of the inner corner of the shoulder, `inner` and `outer` the `across` of the two edges of the lap and
        `start_inner` and `start_outer` where these two edges start. `angle` is the angle between the shoulder and the reference edge.

        """
        sine = math.sin(math.radians(angle))
        cosine = math.cos(math.radians(angle)) * (-1.0 if self._mirrored else 1.0)
        shoulder_run = -(outer - inner) * cosine / sine
        if self.lap_exit == LapExitType.MITRE:
            exit_points = [(corner, inner), (corner + (outer - inner) / math.tan(math.atan2(sine, -cosine) / 2.0), outer)]
        elif self.lap_exit == LapExitType.REBATE:
            rebate = corner + self.rebate_length / sine
            exit_points = [(rebate, inner), (rebate + shoulder_run, outer)]
        else:
            exit_points = [(corner, inner), (corner + shoulder_run, outer)]
        return [(start_inner, inner)] + exit_points + [(start_outer, outer)]


class Dovetail(CornerLock):
    """Represents a Dovetail feature, the corner lock of a log house.

    The tail spans `length` from `start_x` towards the part. Seen from the side of the lap its upper face falls towards the outer edge of the tail, its lower face falls
    towards `start_x`, by `slope` each, so that the tail locks in both directions.

    Parameters
    ----------
    orientation : str
        Which end of the element is processed. :attr:`OrientationType.START` or :attr:`OrientationType.END`.
    cut_off : bool
        True if the element is trimmed at `start_x`. Otherwise the material behind the tail remains.
    start_x : float
        Distance from the start of the element to the end of the tail. -100000.0 < start_x < 100000.0.
    start_y : float
        Width of the lap, measured from the edge of the element which is opposite of the tail. 0.0 < start_y < 50000.0.
    start_depth : float
        Depth, from the reference side, of the reference level of the tail. -50000.0 < start_depth < 50000.0.
    slope : float, optional
        Inclination of the faces of the tail, in degrees. 0.0 < slope < 45.0.
    length : float
        Length of the tail. 0.0 < length < 50000.0.
    rebate_length : float
        Length of the step, if `lap_exit` is :attr:`LapExitType.REBATE`. 0.0 < rebate_length < 50000.0.
    height_ref_side : float
        Height of the upper face above the reference level, at the inner side of the tail. 0.0 < height_ref_side < 50000.0.
    height_opp_side : float
        Depth of the lower face below the reference level, at the shoulder. 0.0 < height_opp_side < 50000.0.
    lap_position : str
        The edge of the element where the tail is. :attr:`EdgePositionType.REFEDGE` or :attr:`EdgePositionType.OPPEDGE`.
    lap_exit : str
        Shape of the transition from the lap to the part. One of :class:`LapExitType`.
    shape : str
        Shape of the sloped faces. One of :class:`DovetailShapeType`.
    process_side : str
        Which of the sloped faces are cut. One of :class:`ProcessSideType`.

    """

    PROCESSING_NAME = "Dovetail"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "CutOff": AttributeSpec("cut_off", bool, False),
        "StartX": AttributeSpec("start_x", float, 0.0, LENGTH_POS, scales=True),
        "StartY": AttributeSpec("start_y", float, 30.0, WIDTH, scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 50.0, WIDTH_N, scales=True),
        "Slope": AttributeSpec("slope", float, None, (0.0, 45.0)),
        "Length": AttributeSpec("length", float, 150.0, WIDTH, scales=True),
        "RebateLength": AttributeSpec("rebate_length", float, 10.0, WIDTH, scales=True),
        "HeightRefSide": AttributeSpec("height_ref_side", float, 60.0, WIDTH, scales=True),
        "HeightOppSide": AttributeSpec("height_opp_side", float, 30.0, WIDTH, scales=True),
        "LapPosition": AttributeSpec("lap_position", str, EdgePositionType.REFEDGE, choices=(EdgePositionType.REFEDGE, EdgePositionType.OPPEDGE)),
        "LapExit": AttributeSpec("lap_exit", str, LapExitType.MITRE, choices=(LapExitType.NONE, LapExitType.MITRE, LapExitType.REBATE)),
        "Shape": AttributeSpec("shape", str, DovetailShapeType.EUROPEAN, choices=(DovetailShapeType.EUROPEAN, DovetailShapeType.AMERICAN)),
        "ProcessSide": AttributeSpec("process_side", str, ProcessSideType.BOTH, choices=(ProcessSideType.BOTH, ProcessSideType.REFSIDE, ProcessSideType.OPPSIDE)),
    }

    def volumes_from_params_and_element(self, element):
        """The volumes this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If `slope` is not set.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        if self.slope is None:
            raise ValueError("The slope of the Dovetail is not set.")
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        to_model = point_mapper(self, element, self._mirrored)
        margin = width + height + self.length + self.height_ref_side + self.height_opp_side + abs(self.start_depth)
        inner = width - self.start_y
        # only the figure of the TyroleanDovetail shows it: without cut_off the material in front of start_x stays
        start = -margin if self.cut_off else 0.0
        volumes = []

        if self.cut_off:
            end = abs(self.start_x) + element.blank_length + margin
            plan = [(-end, -margin), (0.0, -margin), (0.0, width + margin), (-end, width + margin)]
            volumes.append(prism([to_model(a, b, -margin) for a, b in plan], [to_model(a, b, height + margin) for a, b in plan]))

        plan = self._lap_outline(self.length, inner, width + margin, start, start)
        volumes.append(prism([to_model(a, b, -margin) for a, b in plan], [to_model(a, b, height + margin) for a, b in plan]))

        if self.process_side != ProcessSideType.OPPSIDE:
            section = self._upper_section(inner, margin)
            volumes.append(prism([to_model(start, b, d) for b, d in section], [to_model(self.length, b, d) for b, d in section]))
        if self.process_side != ProcessSideType.REFSIDE:
            section = self._lower_section(height, start, margin)
            volumes.append(prism([to_model(a, -margin, d) for a, d in section], [to_model(a, inner + margin, d) for a, d in section]))
        return volumes

    def _upper_section(self, inner, margin):
        # (across, depth) outline of what is above the upper face
        sine, cosine = math.sin(math.radians(self.slope)), math.cos(math.radians(self.slope))
        peak = self.start_depth - self.height_ref_side
        outer_depth = peak + (inner + margin) * sine / cosine
        top = min(peak, 0.0) - margin
        if self.shape == DovetailShapeType.EUROPEAN:
            # the hook runs from the reference level at the inner side of the tail, perpendicular to the upper face
            hook = self.height_ref_side * cosine
            face = [(inner, self.start_depth), (inner - hook * sine, self.start_depth - hook * cosine)]
        else:
            face = [(inner, peak)]
        return [(inner + margin, face[0][1])] + face + [(-margin, outer_depth), (-margin, top), (inner + margin, top)]

    def _lower_section(self, height, start, margin):
        # (along, depth) outline of what is below the lower face
        sine, cosine = math.sin(math.radians(self.slope)), math.cos(math.radians(self.slope))
        shoulder_depth = self.start_depth + self.height_opp_side
        start_depth = shoulder_depth + (self.length - start) * sine / cosine
        bottom = max(start_depth, height) + margin
        if self.shape == DovetailShapeType.EUROPEAN:
            # the hook runs to the corner of the shoulder and the opposite side, perpendicular to the lower face
            hook = (height - shoulder_depth) * cosine
            ridge = (self.length - hook * sine, height - hook * cosine)
            run = (bottom - height) / cosine
            return [(start, start_depth), ridge, (self.length + run * sine, bottom), (start, bottom)]
        return [(start, start_depth), (self.length, shoulder_depth), (self.length, bottom), (start, bottom)]
