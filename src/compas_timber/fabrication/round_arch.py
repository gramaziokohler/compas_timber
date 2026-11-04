import math

from compas.geometry import Point

from .btlx import AttributeSpec
from .btlx import ParametricProcessing
from .profile_front import ArcShapeType
from .profile_front import PremillType
from .profile_front import element_size
from .profile_front import exit_point
from .profile_front import extruded_volume
from .profile_front import polyline_curves
from .profile_front import segment_curves


class RoundArch(ParametricProcessing):
    """Represents a Round Arch feature to be made on a beam: a circular arc, extruded across the reference side.

    The arc lies in the plane of the X-axis and the normal of the reference side, and is cut through the whole element.

    Parameters
    ----------
    start_x : float
        Distance from the start of the reference side to the middle of the arc, along X.
    length : float
        Length of the chord of the arc.
    camber : float
        Height of the arc above its chord.
    arc_shape : str
        `concave` for a hollow whose chord lies on the reference side. `convex` for a crown which touches the reference side,
        with its chord at the depth of `camber`, and with the material on both sides of it removed down to the chord.
    premill : str
        How the ends of a `convex` arc connect to the reference side. One of :class:`~compas_timber.fabrication.PremillType`.

    """

    PROCESSING_NAME = "RoundArch"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Length": AttributeSpec("length", float, 500.0, (0.0, 100000.0), scales=True),
        "Camber": AttributeSpec("camber", float, 30.0, (0.0, 1000.0), scales=True),
        "ArcShape": AttributeSpec("arc_shape", str, ArcShapeType.CONCAVE, choices=(ArcShapeType.CONVEX, ArcShapeType.CONCAVE)),
        "Premill": AttributeSpec("premill", str, PremillType.ANGULAR, choices=(PremillType.ROUND, PremillType.ANGULAR)),
    }

    def volumes_from_params_and_element(self, element):
        """The volume between the arc and the reference side.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates. Empty if the arc leaves the element as it is.

        """
        if not self.length or not self.camber:
            return []
        half = self.length / 2.0
        convex = self.arc_shape == ArcShapeType.CONVEX
        z = -self.camber if convex else 0.0
        start, end = Point(-half, 0.0, z), Point(half, 0.0, z)

        slope = (0.0, 1.0)
        if convex and self.premill == PremillType.ANGULAR:
            angle = 2.0 * math.atan(2.0 * self.camber / self.length)  # of the arc at its ends: the premill is normal to it
            slope = (math.sin(angle), math.cos(angle))
        # shortcut: a round premill is a wall at the end of the arc, the figure's tool radius is not a parameter, upgrade if it ever is
        height = element_size(element)
        before = exit_point(start, (-slope[0], slope[1]), height)
        after = exit_point(end, slope, height)

        curves = polyline_curves([before, start]) + segment_curves(start, end, self.camber if convex else -self.camber) + polyline_curves([end, after, before])
        return [extruded_volume(curves, self.start_x, element, self.ref_side_index)]
