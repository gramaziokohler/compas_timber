import math

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_brep import Brep

from .btlx import AlignmentType
from .btlx import AttributeSpec
from .btlx import MachiningLimits
from .btlx import ParametricProcessing


class SawCutMachiningLimits(MachiningLimits):
    """The limited faces of a :class:`SawCut`. Unlike the common :class:`MachiningLimits` it only has three.

    Parameters
    ----------
    face_limited_start : bool, optional
        If True the cut stops at its start point, otherwise it continues backwards out of the element.
    face_limited_end : bool, optional
        If True the cut stops after its length, otherwise it continues out of the element.
    face_limited_bottom : bool, optional
        If True the cut stops at its depth, otherwise it continues out of the element.

    """

    EXPECTED_KEYS = ["FaceLimitedStart", "FaceLimitedEnd", "FaceLimitedBottom"]

    def __init__(self, face_limited_start=True, face_limited_end=True, face_limited_bottom=True):
        super(SawCutMachiningLimits, self).__init__(face_limited_start=face_limited_start, face_limited_end=face_limited_end, face_limited_bottom=face_limited_bottom)

    def as_dict(self):
        """The limits by their BTLx names, with boolean values."""
        limits = super(SawCutMachiningLimits, self).as_dict()
        return {key: limits[key] for key in self.EXPECTED_KEYS}


class SawCut(ParametricProcessing):
    """Cuts a saw kerf along a line, at a depth below the reference side.

    Parameters
    ----------
    start_x : float
        Distance of the start point along the reference edge.
    start_y : float
        Distance of the start point from the reference edge.
    start_depth : float
        Distance of the start point below the reference side. This is the upper limit of the cut.
    angle : float
        Angle, in degrees, in the reference side, from the direction towards the element's start (-X) to the direction of the cut, clockwise when looking at the side.
        The default of 90 points away from the reference edge (+Y).
    inclination : float
        Angle, in degrees, between the reference side, on the left of the direction of the cut, and the saw plane.
    bevel : float
        Angle, in degrees, inside the saw plane, of the lower limit of the cut. Positive values make the cut deeper at its end.
    length : float
        Length of the cut, along its direction.
    depth : float
        Depth of the cut at its start point, perpendicular to the reference side and measured from `start_depth`.
    machining_limits : :class:`SawCutMachiningLimits` or dict, optional
        The limited faces of the cut. All are limited if omitted.
    tool_position : str, optional
        Position of the blade relative to the line, looking along the direction of the cut. One of `left`, `center` or `right`.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "SawCut"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 0.0, (-50000.0, 50000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 0.0, (-50000.0, 50000.0), scales=True),
        "Angle": AttributeSpec("angle", float, 90.0, (-180.0, 180.0)),
        "Inclination": AttributeSpec("inclination", float, 90.0, (0.1, 179.9)),
        "Bevel": AttributeSpec("bevel", float, 0.0, (-89.9, 89.9)),
        "Length": AttributeSpec("length", float, 100.0, (0.0, 100000.0), scales=True),
        "Depth": AttributeSpec("depth", float, 50.0, (0.0, 50000.0), scales=True),
        "MachiningLimits": AttributeSpec("machining_limits", SawCutMachiningLimits),
    }

    # shortcut: the blade thickness is not in BTLx, so the kerf is this fraction of the element's smaller dimension, which needs no units. Upgrade if tools get modeled
    KERF_RATIO = 0.02

    def __init__(self, tool_position=AlignmentType.LEFT, **kwargs):
        if tool_position not in (AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT):
            raise ValueError("tool_position must be one of left, center or right. Got: {}".format(tool_position))
        super(SawCut, self).__init__(tool_position=tool_position, **kwargs)

    @property
    def __data__(self):
        data = super(SawCut, self).__data__
        if self.machining_limits:
            data["machining_limits"] = self.machining_limits.as_dict()
        return data

    @property
    def machining_limits(self):
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        if isinstance(machining_limits, dict):
            machining_limits = SawCutMachiningLimits.from_dict(machining_limits)
        if machining_limits is not None and not isinstance(machining_limits, SawCutMachiningLimits):
            raise ValueError("machining_limits must be SawCutMachiningLimits. Got: {}".format(machining_limits))
        self._machining_limits = machining_limits

    @classmethod
    def from_line_and_element(cls, line, element, depth, ref_side_index=0, **kwargs):
        """Construct a SawCut from its upper limit.

        Parameters
        ----------
        line : :class:`~compas.geometry.Line`
            The upper limit of the cut, from its start point. It must be parallel to the reference side.
        element : :class:`~compas_timber.base.TimberElement`
            The element to cut.
        depth : float
            The depth of the cut.
        ref_side_index : int, optional
            The index of the reference side the parameters refer to.
        **kwargs : dict, optional
            Additional keyword arguments of the processing.

        Returns
        -------
        :class:`~compas_timber.fabrication.SawCut`

        """
        ref_side = element.ref_sides[ref_side_index]
        start = ref_side.to_local_coordinates(line.start)
        end = ref_side.to_local_coordinates(line.end)
        return cls(
            start_x=start.x,
            start_y=start.y,
            start_depth=-start.z,
            angle=math.degrees(math.atan2(end.y - start.y, start.x - end.x)),
            length=math.hypot(end.x - start.x, end.y - start.y),
            depth=depth,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, line, element, depth, **kwargs):
        """Construct a SawCut from a line, see :meth:`from_line_and_element`."""
        return cls.from_line_and_element(line, element, depth, **kwargs)

    def volumes_from_params_and_element(self, element):
        """The saw kerf.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        limits = self.machining_limits or SawCutMachiningLimits()
        angle = math.radians(self.angle)
        inclination = math.radians(self.inclination)
        bevel = math.radians(self.bevel)

        # saw frame: X along the cut, Y down the saw plane, Z to the left of the cut
        direction = Vector(-math.cos(angle), math.sin(angle), 0.0)
        left = Vector(-math.sin(angle), -math.cos(angle), 0.0)
        down = left * math.cos(inclination) - Vector(0.0, 0.0, math.sin(inclination))
        saw_frame = Frame(Point(self.start_x, self.start_y, -self.start_depth), direction, down)

        reach = element.blank_length + element.width + element.height + self.length + abs(self.start_x) + abs(self.start_y) + abs(self.start_depth)
        x_start = 0.0 if limits.face_limited_start else -reach
        x_end = self.length if limits.face_limited_end else reach
        if x_start == x_end:
            return []

        kerf = self.KERF_RATIO * min(element.width, element.height)
        z_start = {AlignmentType.LEFT: 0.0, AlignmentType.CENTER: -0.5 * kerf, AlignmentType.RIGHT: -kerf}[self.tool_position]
        center = Point(0.5 * (x_start + x_end), 0.5 * reach, z_start + 0.5 * kerf)
        volume = Brep.from_box(Box(x_end - x_start, reach, kerf, Frame(center, [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))
        if limits.face_limited_bottom:
            # Brep.trimmed() keeps what is behind the plane
            lower_limit = Point(0.0, self.depth / math.sin(inclination), 0.0)
            volume = volume.trimmed(Plane(lower_limit, Vector(-math.sin(bevel), math.cos(bevel), 0.0)))

        ref_side = element.ref_sides[self.ref_side_index]
        return [volume.transformed(Transformation.from_frame(ref_side) * Transformation.from_frame(saw_frame))]
