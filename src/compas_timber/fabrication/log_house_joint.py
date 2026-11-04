from compas.geometry import Cylinder
from compas.geometry import Line
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import ParametricProcessing
from .log_house_half_lap import prism


class LogLapPositionType(object):
    """Enum for the position of the side laps of a :class:`LogHouseJoint`.

    Attributes
    ----------
    SYMMETRIC : literal("symmetric")
        Both side laps are centered on the joint.
    FORWARD : literal("forward")
        The lap at the reference edge starts with the notches and overhangs them towards the end of the part. The lap at the opposite edge ends with them.
    BACKWARD : literal("backward")
        The lap at the reference edge ends with the notches and overhangs them towards the start of the part. The lap at the opposite edge starts with them.

    """

    SYMMETRIC = "symmetric"
    FORWARD = "forward"
    BACKWARD = "backward"


class LogHouseJoint(ParametricProcessing):
    """Represents a Log House Joint feature to be made on a beam.

    Four recesses around the part, which leave a neck where two logs cross: a notch across the width in the reference side, another one in the opposite side,
    and a lap running down each edge, optionally with arcs which widen the laps towards the ends of the logs' height.

    Parameters
    ----------
    start_x : float
        The position along the part of the middle of the notches. -100000.0 <= start_x <= 100000.0.
    side_laps_limited : bool
        If True, the laps stop at ``depth_side_laps``. Otherwise, they run through the height of the part.
    depth_side_laps : float, optional
        The distance of the bottom of the laps from the reference side. Required if the laps are limited. 0.0 <= depth_side_laps <= 50000.0.
    lap_position : str
        The position of the laps relative to the notches. One of the values of :class:`LogLapPositionType`.
    length_ref_side : float
        The length of the notch in the reference side. 0.0 <= length_ref_side <= 50000.0.
    depth_ref_side : float
        The depth of the notch in the reference side. 0.0 <= depth_ref_side <= 50000.0.
    length_opp_side : float
        The length of the notch in the side opposite of the reference side. 0.0 <= length_opp_side <= 50000.0.
    depth_opp_side : float
        The depth of the notch in the side opposite of the reference side. 0.0 <= depth_opp_side <= 50000.0.
    length_ref_edge : float
        The length of the lap at the reference edge. 0.0 <= length_ref_edge <= 50000.0.
    depth_ref_edge : float
        The depth of the lap at the reference edge, measured in the reference side. 0.0 <= depth_ref_edge <= 50000.0.
    length_opp_edge : float
        The length of the lap at the edge opposite of the reference edge. 0.0 <= length_opp_edge <= 50000.0.
    depth_opp_edge : float
        The depth of the lap at that edge, measured in the reference side. 0.0 <= depth_opp_edge <= 50000.0.
    drillhole : bool
        If True, a hole is requested. It has no effect on the geometry.
    arc_ref_edge_start : bool
        If True, the wall towards the start of the lap at the reference edge gets arcs.
    arc_ref_edge_end : bool
        If True, the wall towards the end of the lap at the reference edge gets arcs.
    arc_opp_edge_start : bool
        If True, the wall towards the start of the lap at the opposite edge gets arcs.
    arc_opp_edge_end : bool
        If True, the wall towards the end of the lap at the opposite edge gets arcs.
    arc_radius : float
        The radius of the arcs. 0.0 <= arc_radius <= 50000.0.
    arc_depth : float
        The depth below the reference side at which the arcs of a wall meet. -50000.0 <= arc_depth <= 50000.0.
    arc_center : float
        The distance along the part between ``start_x`` and the centers of the arcs, which are on the reference side. The arcs of a wall have the center
        on the far side of ``start_x``. 0.0 <= arc_center <= 50000.0.

    """

    PROCESSING_NAME = "LogHouseJoint"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "SideLapsLimited": AttributeSpec("side_laps_limited", bool, False),
        "DepthSideLaps": AttributeSpec("depth_side_laps", float, None, (0.0, 50000.0), scales=True),
        "LapPosition": AttributeSpec(
            "lap_position", str, LogLapPositionType.SYMMETRIC, choices=(LogLapPositionType.SYMMETRIC, LogLapPositionType.FORWARD, LogLapPositionType.BACKWARD)
        ),
        "LengthRefSide": AttributeSpec("length_ref_side", float, 100.0, (0.0, 50000.0), scales=True),
        "DepthRefSide": AttributeSpec("depth_ref_side", float, 10.0, (0.0, 50000.0), scales=True),
        "LengthOppSide": AttributeSpec("length_opp_side", float, 100.0, (0.0, 50000.0), scales=True),
        "DepthOppSide": AttributeSpec("depth_opp_side", float, 10.0, (0.0, 50000.0), scales=True),
        "LengthRefEdge": AttributeSpec("length_ref_edge", float, 100.0, (0.0, 50000.0), scales=True),
        "DepthRefEdge": AttributeSpec("depth_ref_edge", float, 10.0, (0.0, 50000.0), scales=True),
        "LengthOppEdge": AttributeSpec("length_opp_edge", float, 100.0, (0.0, 50000.0), scales=True),
        "DepthOppEdge": AttributeSpec("depth_opp_edge", float, 10.0, (0.0, 50000.0), scales=True),
        "Drillhole": AttributeSpec("drillhole", bool, False),
        "ArcRefEdgeStart": AttributeSpec("arc_ref_edge_start", bool, False),
        "ArcRefEdgeEnd": AttributeSpec("arc_ref_edge_end", bool, False),
        "ArcOppEdgeStart": AttributeSpec("arc_opp_edge_start", bool, False),
        "ArcOppEdgeEnd": AttributeSpec("arc_opp_edge_end", bool, False),
        "ArcRadius": AttributeSpec("arc_radius", float, 120.0, (0.0, 50000.0), scales=True),
        "ArcDepth": AttributeSpec("arc_depth", float, 60.0, (-50000.0, 50000.0), scales=True),
        "ArcCenter": AttributeSpec("arc_center", float, 120.0, (0.0, 50000.0), scales=True),
    }

    def _lap_ranges(self):
        """The start and end along the part of the laps at the reference edge and the opposite edge."""
        # shortcut: the figure only shows notches of equal length, so the laps align with the one in the reference side. Upgrade if a machine's interpretation is known.
        notch_start = self.start_x - 0.5 * self.length_ref_side
        notch_end = self.start_x + 0.5 * self.length_ref_side
        if self.lap_position == LogLapPositionType.FORWARD:
            return (notch_start, notch_start + self.length_ref_edge), (notch_end - self.length_opp_edge, notch_end)
        if self.lap_position == LogLapPositionType.BACKWARD:
            return (notch_end - self.length_ref_edge, notch_end), (notch_start, notch_start + self.length_opp_edge)
        half_ref, half_opp = 0.5 * self.length_ref_edge, 0.5 * self.length_opp_edge
        return (self.start_x - half_ref, self.start_x + half_ref), (self.start_x - half_opp, self.start_x + half_opp)

    def volumes_from_params_and_element(self, element):
        """The notches and the laps of the joint, followed by the arcs.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the laps are limited, but `depth_side_laps` is not set.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        # shortcut: drillhole is not modelled, the specification gives neither its position nor its size. Upgrade if a machine's interpretation is known.
        if self.side_laps_limited and self.depth_side_laps is None:
            raise ValueError("The side laps are limited, but depth_side_laps is not set.")

        ref_side = element.ref_sides[self.ref_side_index]
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        clear = width + height  # past the faces, for a clean cut
        laps_bottom = self.depth_side_laps if self.side_laps_limited else height + clear

        def block(x_range, y_range, depth_range):
            """A box given by its ranges in the reference side, and the depth below it."""
            (x_min, x_max), (y_min, y_max), (top, bottom) = x_range, y_range, depth_range
            return prism(ref_side, [(x_min, y_min, -top), (x_max, y_min, -top), (x_max, y_max, -top), (x_min, y_max, -top)], top - bottom)

        def arcs(wall, lap, y_range, toward_center):
            """The material between a lap's wall and its two arcs, which is inside of the arcs' circles."""
            center = self.start_x + self.arc_center * toward_center
            if self.arc_radius <= abs(center - wall):
                return []
            farthest = center - self.arc_radius * toward_center
            inside_lap = wall + 0.5 * (lap[1] - lap[0]) * toward_center  # overlaps the lap, so that the volume does not end on the lap's wall
            x_range = (min(farthest, inside_lap), max(farthest, inside_lap))

            volumes = []
            for center_depth, depth_range in ((0.0, (-clear, self.arc_depth)), (2.0 * self.arc_depth, (self.arc_depth, laps_bottom))):
                depth_range = (depth_range[0], min(depth_range[1], laps_bottom))
                if depth_range[0] >= depth_range[1]:
                    continue
                axis = Line(ref_side.to_world_coordinates([center, y_range[0] - 1.0, -center_depth]), ref_side.to_world_coordinates([center, y_range[1] + 1.0, -center_depth]))
                circle = Brep.from_cylinder(Cylinder.from_line_and_radius(axis, self.arc_radius))
                volumes.extend(Brep.from_boolean_intersection(circle, block(x_range, y_range, depth_range)))
            return volumes

        volumes = []
        across = (-clear, width + clear)
        if self.length_ref_side and self.depth_ref_side:
            half = 0.5 * self.length_ref_side
            volumes.append(block((self.start_x - half, self.start_x + half), across, (-clear, self.depth_ref_side)))
        if self.length_opp_side and self.depth_opp_side:
            half = 0.5 * self.length_opp_side
            volumes.append(block((self.start_x - half, self.start_x + half), across, (height - self.depth_opp_side, height + clear)))

        ref_lap, opp_lap = self._lap_ranges()
        ref_edge = (-clear, self.depth_ref_edge)
        opp_edge = (width - self.depth_opp_edge, width + clear)
        arc_volumes = []
        for lap, depth, y_range, arc_start, arc_end in (
            (ref_lap, self.depth_ref_edge, ref_edge, self.arc_ref_edge_start, self.arc_ref_edge_end),
            (opp_lap, self.depth_opp_edge, opp_edge, self.arc_opp_edge_start, self.arc_opp_edge_end),
        ):
            if not depth or lap[0] == lap[1] or not laps_bottom:
                continue
            volumes.append(block(lap, y_range, (-clear, laps_bottom)))
            if arc_start:
                arc_volumes.extend(arcs(lap[0], lap, y_range, 1.0))
            if arc_end:
                arc_volumes.extend(arcs(lap[1], lap, y_range, -1.0))
        return volumes + arc_volumes
