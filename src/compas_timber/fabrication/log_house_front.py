import math

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .log_house_half_lap import prism


class LogHouseFront(ParametricProcessing):
    """Represents a Log House Front feature to be made on a beam.

    Trims the end of the part along a wall perpendicular to the reference side, even if this removes the reference edge's corner, and lowers the sides of the remaining
    end to a sloped plane, which stops at a shoulder parallel to the trimmed wall.

    Parameters
    ----------
    orientation : str
        The end of the part to trim. ``OrientationType.START`` or ``OrientationType.END``.
    start_x : float
        The position along the reference edge of the trimmed wall. -100000.0 <= start_x <= 100000.0.
    start_depth : float
        The depth of the sloped plane at the trimmed wall, at the reference edge. 0.0 <= start_depth <= 50000.0.
    angle : float
        The angle in the reference side between the trimmed wall and the reference edge, measured from the part of the edge which faces the trimmed end.
        0.1 <= angle <= 179.9.
    length : float
        The distance between the trimmed wall and the shoulder, perpendicular to them. 0.0 <= length <= 50000.0.
    depth_ref_edge : float
        The depth of the sloped plane at the shoulder, at the reference edge. 0.0 <= depth_ref_edge <= 50000.0.
    depth_opp_edge : float
        The depth of the sloped plane at the trimmed wall, at the edge opposite of the reference edge. 0.0 <= depth_opp_edge <= 50000.0.
    ref_side_only : bool
        If True, only the reference side is lowered. Otherwise, the opposite side is lowered too, by the same depths measured from that side.

    """

    PROCESSING_NAME = "LogHouseFront"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 20.0, (0.0, 50000.0), scales=True),
        "Angle": AttributeSpec("angle", float, 90.0, (0.1, 179.9)),
        "Length": AttributeSpec("length", float, 120.0, (0.0, 50000.0), scales=True),
        "DepthRefEdge": AttributeSpec("depth_ref_edge", float, 20.0, (0.0, 50000.0), scales=True),
        "DepthOppEdge": AttributeSpec("depth_opp_edge", float, 20.0, (0.0, 50000.0), scales=True),
        "RefSideOnly": AttributeSpec("ref_side_only", bool, False),
    }

    def volumes_from_params_and_element(self, element):
        """The trimmed end of the element, followed by the material above the sloped planes.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        ref_side = element.ref_sides[self.ref_side_index]
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        start = self.orientation == OrientationType.START
        angle = math.radians(self.angle)
        shift = 1.0 / math.tan(angle) * (-1.0 if start else 1.0)  # the wall's change in x per unit of y
        y_near, y_far = -width, 2.0 * width  # past the edges, for a clean cut

        wall_near = self.start_x + shift * y_near
        wall_far = self.start_x + shift * y_far
        beyond = min(wall_near, wall_far, 0.0) - height if start else max(wall_near, wall_far, element.blank_length) + height
        trim = [(wall_near, y_near, height), (wall_far, y_far, height), (beyond, y_far, height), (beyond, y_near, height)]
        volumes = [prism(ref_side, trim, -3.0 * height)]

        if not self.length or not (self.start_depth or self.depth_ref_edge or self.depth_opp_edge):
            return volumes

        to_shoulder = self.length / math.sin(angle) * (1.0 if start else -1.0)  # along the reference edge

        def corner(position, y):
            """Maps a position in the plane, which is 0.0 at the wall and 1.0 at the shoulder, to its x, y and depth."""
            depth = self.start_depth + (self.depth_ref_edge - self.start_depth) * position + (self.depth_opp_edge - self.start_depth) * y / width
            return self.start_x + shift * y + to_shoulder * position, y, depth

        # past the wall too, where the material is already gone, so that the plane's outline does not coincide with the trimmed face.
        corners = [corner(-1.0, y_near), corner(1.0, y_near), corner(1.0, y_far), corner(-1.0, y_far)]
        clearance = max(depth for _, _, depth in corners) + height
        volumes.append(prism(ref_side, [(x, y, -depth) for x, y, depth in corners], clearance))
        if not self.ref_side_only:
            volumes.append(prism(ref_side, [(x, y, depth - height) for x, y, depth in corners], -clearance))
        return volumes
