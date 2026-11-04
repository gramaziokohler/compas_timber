import math

from compas.geometry import Point
from compas_brep.curves import NurbsCurve

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .profile_front import PremillType
from .profile_front import closed_towards_head
from .profile_front import element_size
from .profile_front import exit_point
from .profile_front import extruded_volume
from .profile_front import polyline_curves


def _largest_root(value):
    """Returns the largest real solution of 4v^3 - 3v = value, for value >= -1."""
    return math.cos(math.acos(value) / 3.0) if value <= 1.0 else math.cosh(math.acosh(value) / 3.0)


class ProfileCambered(ParametricProcessing):
    """Represents a Profile Cambered feature to be made on a beam: a cubic curve, extruded across the reference side.

    The curve lies in the plane of the X-axis and the normal of the reference side, and is cut through the whole element.
    Between the curve and the end the orientation names, the element is cut down to `start_depth`.

    Parameters
    ----------
    orientation : str
        The end of the element the curve starts from. One of :class:`~compas_timber.fabrication.OrientationType`.
    start_x : float
        Distance from the start of the reference side to the start of the curve, along X.
    length : float
        Length of the curve along X, from `start_x` away from the end of the element named by `orientation`.
    start_depth : float
        Depth of the start of the curve below the reference side.
    max_depth : float
        Depth of the local maximum of the curve, the first of its two extrema.
    min_depth : float
        Depth of the local minimum of the curve, the second of its two extrema.
    end_depth : float
        Depth of the end of the curve.
    premill : str
        How the end of the curve connects to the reference side. One of :class:`~compas_timber.fabrication.PremillType`.

    """

    PROCESSING_NAME = "ProfileCambered"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Length": AttributeSpec("length", float, 0.0, (0.0, 100000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 40.0, (0.0, 1000.0), scales=True),
        "MaxDepth": AttributeSpec("max_depth", float, 60.0, (0.0, 1000.0), scales=True),
        "MinDepth": AttributeSpec("min_depth", float, 10.0, (0.0, 1000.0), scales=True),
        "EndDepth": AttributeSpec("end_depth", float, 40.0, (0.0, 1000.0), scales=True),
        "Premill": AttributeSpec("premill", str, PremillType.ANGULAR, choices=(PremillType.ROUND, PremillType.ANGULAR)),
    }

    def volumes_from_params_and_element(self, element):
        """The volume above the curve and towards the end of the element.

        With v = -1/2 at the maximum and v = 1/2 at the minimum, every such cubic is `max - range * (1/2 + 3/2 v - 2 v^3)`,
        so the start and the end of the curve are the solutions of 4v^3 - 3v = c.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the curve has no length, or no cubic reaches the depths.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        depth_range = self.max_depth - self.min_depth
        if not self.length or depth_range <= 0.0 or self.start_depth > self.max_depth or self.end_depth < self.min_depth:
            raise ValueError("No cubic of length {} reaches these depths: the curve needs start <= max, end >= min and min < max.".format(self.length))

        v_start = -_largest_root(2.0 * (self.max_depth - self.start_depth) / depth_range - 1.0)
        v_end = _largest_root(1.0 - 2.0 * (self.max_depth - self.end_depth) / depth_range)
        span = v_end - v_start

        def slope(v):  # of the depth, along the length of the curve
            return depth_range * (6.0 * v**2 - 1.5) * span / self.length

        third = self.length / 3.0
        depths = [self.start_depth, self.start_depth + slope(v_start) * third, self.end_depth - slope(v_end) * third, self.end_depth]
        curve = NurbsCurve.from_parameters([Point(i * third, 0.0, -d) for i, d in enumerate(depths)], [1.0] * 4, [0.0, 1.0], [4, 4], 3)

        end = Point(self.length, 0.0, -self.end_depth)
        # shortcut: a round premill is a wall at the end of the curve, the figure's tool radius is not a parameter, upgrade if it ever is
        direction = (slope(v_end), 1.0) if self.premill == PremillType.ANGULAR else (0.0, 1.0)
        curves = [curve] + polyline_curves([end, exit_point(end, direction, element_size(element))])
        return [extruded_volume(closed_towards_head(curves, self.start_x, element), self.start_x, element, self.ref_side_index, self.orientation)]
