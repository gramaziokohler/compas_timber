import math

from .btlx import AttributeSpec
from .btlx import ParametricProcessing


class MarkingStyleType(object):
    """Enum for the shape of a :class:`Marking`.

    Attributes
    ----------
    SINGLE : literal("single")
        One line.
    DOUBLE : literal("double")
        Two parallel lines.
    SQUARE : literal("square")
        A closed parallelogram.
    """

    SINGLE = "single"
    DOUBLE = "double"
    SQUARE = "square"


class Marking(ParametricProcessing):
    """Marks lines on a reference side. This leaves the geometry of the element as it is.

    Parameters
    ----------
    start_x : float
        Distance of the start point along the reference edge.
    start_y : float
        Distance of the start point from the reference edge.
    angle : float
        Angle, in degrees, from the direction towards the element's start (-X) to the first line, clockwise when looking at the side.
    length_limited : bool
        If True the lines have the given `length`. The figure does not show the False case, which reads as lines across the whole side.
    length : float
        Length of the lines.
    width : float
        Distance from the start point to the start of the second line, for the styles `double` and `square`.
    interior_angle : float
        Angle, in degrees, clockwise from the first line to the direction of `width`, for the styles `double` and `square`.
    style : str
        The shape of the marking, see :class:`MarkingStyleType`.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "Marking"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 0.0, (-50000.0, 50000.0), scales=True),
        "Angle": AttributeSpec("angle", float, 0.0, (-180.0, 180.0)),
        "LengthLimited": AttributeSpec("length_limited", bool, False),
        "Length": AttributeSpec("length", float, 20.0, (0.0, 50000.0), scales=True),
        "Width": AttributeSpec("width", float, 100.0, (0.0, 50000.0), scales=True),
        "InteriorAngle": AttributeSpec("interior_angle", float, 90.0, (0.1, 179.9)),
        "Style": AttributeSpec("style", str, MarkingStyleType.SINGLE, choices=(MarkingStyleType.SINGLE, MarkingStyleType.DOUBLE, MarkingStyleType.SQUARE)),
    }

    @classmethod
    def from_line_and_element(cls, line, element, ref_side_index=0, **kwargs):
        """Construct a single line Marking.

        Parameters
        ----------
        line : :class:`~compas.geometry.Line`
            The line, which is projected onto the reference side.
        element : :class:`~compas_timber.base.TimberElement`
            The element to mark.
        ref_side_index : int, optional
            The index of the reference side the marking is on.
        **kwargs : dict, optional
            Additional keyword arguments of the processing.

        Returns
        -------
        :class:`~compas_timber.fabrication.Marking`

        """
        ref_side = element.ref_sides[ref_side_index]
        start = ref_side.to_local_coordinates(line.start)
        end = ref_side.to_local_coordinates(line.end)
        return cls(
            start_x=start.x,
            start_y=start.y,
            angle=math.degrees(math.atan2(end.y - start.y, start.x - end.x)),
            length_limited=True,
            length=math.hypot(end.x - start.x, end.y - start.y),
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, line, element, **kwargs):
        """Construct a Marking from a line, see :meth:`from_line_and_element`."""
        return cls.from_line_and_element(line, element, **kwargs)
