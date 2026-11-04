import math

from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.geometry import brep_from_outlines

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing


def prism(frame, outline, height):
    """The solid swept by an outline along the Z axis of a frame.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The frame the coordinates of the outline refer to.
    outline : list(tuple(float, float, float))
        The corners of the outline, which must be planar. Sloped outlines keep their slope, so the sides stay parallel to Z.
    height : float
        The distance to sweep the outline along the Z axis of the frame. Negative to sweep it the other way.

    Returns
    -------
    :class:`~compas_brep.Brep`
        The solid, in the coordinates of the frame's parent.

    """
    base = Polyline([frame.to_world_coordinates(Point(*corner)) for corner in outline + outline[:1]])
    vector = frame.zaxis * height
    return brep_from_outlines(base, base.translated(vector), vector)


class LogHouseHalfLap(ParametricProcessing):
    """Represents a Log House Half Lap feature to be made on a beam.

    Two notches of equal outline, one in the reference side and one in the opposite side, each running across the whole width of the reference side.

    Parameters
    ----------
    orientation : str
        ``OrientationType.START`` measures the angle from the part of the reference edge facing the start, ``OrientationType.END`` from the part facing the end.
    start_x : float
        The position along the reference edge of the middle of the notches. -100000.0 <= start_x <= 100000.0.
    angle : float
        The angle in the reference side between the reference edge and the walls of the notches. 0.1 <= angle <= 179.9.
    length : float
        The distance between the walls of the notches, perpendicular to them. 0.0 <= length <= 50000.0.
    depth_ref_side : float
        The depth of the notch in the reference side. 0.0 <= depth_ref_side <= 50000.0.
    depth_opp_side : float
        The depth of the notch in the side opposite of the reference side. 0.0 <= depth_opp_side <= 50000.0.

    """

    PROCESSING_NAME = "LogHouseHalfLap"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Angle": AttributeSpec("angle", float, 90.0, (0.1, 179.9)),
        "Length": AttributeSpec("length", float, 120.0, (0.0, 50000.0), scales=True),
        "DepthRefSide": AttributeSpec("depth_ref_side", float, 20.0, (0.0, 50000.0), scales=True),
        "DepthOppSide": AttributeSpec("depth_opp_side", float, 20.0, (0.0, 50000.0), scales=True),
    }

    def volumes_from_params_and_element(self, element):
        """The notches removed from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        if not self.length:
            return []
        ref_side = element.ref_sides[self.ref_side_index]
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        angle = math.radians(self.angle)
        shift = 1.0 / math.tan(angle) * (-1.0 if self.orientation == OrientationType.START else 1.0)  # the walls' change in x per unit of y
        half_length = 0.5 * self.length / math.sin(angle)  # along the reference edge

        y_near, y_far = -width, 2.0 * width  # past the edges, for a clean cut
        corners = [
            (self.start_x + shift * y_near - half_length, y_near),
            (self.start_x + shift * y_near + half_length, y_near),
            (self.start_x + shift * y_far + half_length, y_far),
            (self.start_x + shift * y_far - half_length, y_far),
        ]
        volumes = []
        if self.depth_ref_side:
            volumes.append(prism(ref_side, [(x, y, -self.depth_ref_side) for x, y in corners], self.depth_ref_side + height))
        if self.depth_opp_side:
            volumes.append(prism(ref_side, [(x, y, self.depth_opp_side - height) for x, y in corners], -self.depth_opp_side - height))
        return volumes
