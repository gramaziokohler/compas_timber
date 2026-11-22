import math

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import ParametricProcessing


class RidgeValleyCut(ParametricProcessing):
    """Cuts two inclined planes, which meet in a line parallel to the element's axis, into a reference side.

    The material above both planes is removed. With positive inclinations the planes drop away from their
    common line, which leaves a ridge. With negative inclinations they rise from it, which cuts a valley.

    Parameters
    ----------
    start_x : float
        Distance along the reference edge from the start of the element to the start of the ridge line. Also the reference of `length`.
    start_y : float
        Distance from the reference edge to the ridge line.
    start_depth : float
        Distance of the ridge line below the reference side.
    inclination_ref_side : float
        Angle, in degrees, of the plane on the reference edge's side, from the plane parallel to the reference side through the ridge line.
    inclination_opp_side : float
        Angle, in degrees, of the plane on the opposite edge's side, from the plane parallel to the reference side through the ridge line.
    start_limited : bool
        If True the cut stops at `start_x`, otherwise it runs through the start of the element.
    end_limited : bool
        If True the cut stops at `start_x` + `length`, otherwise it runs through the end of the element.
    length : float
        Length of the ridge line.
    angle_ref_edge_start : float
        Angle, in degrees, inside the plane on the reference edge's side, between the ridge line and the line limiting the cut at its start.
    angle_ref_edge_end : float
        Same as `angle_ref_edge_start`, at the end of the cut.
    angle_opp_edge_start : float
        Angle, in degrees, inside the plane on the opposite edge's side, between the ridge line and the line limiting the cut at its start.
    angle_opp_edge_end : float
        Same as `angle_opp_edge_start`, at the end of the cut.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "RidgeValleyCut"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 50.0, (0.0, 50000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 0.0, (-50000.0, 50000.0), scales=True),
        "InclinationRefSide": AttributeSpec("inclination_ref_side", float, 45.0, (-89.9, 89.9)),
        "InclinationOppSide": AttributeSpec("inclination_opp_side", float, 45.0, (-89.9, 89.9)),
        "StartLimited": AttributeSpec("start_limited", bool, False),
        "EndLimited": AttributeSpec("end_limited", bool, False),
        "Length": AttributeSpec("length", float, 0.0, (0.0, 100000.0), scales=True),
        "AngleRefEdgeStart": AttributeSpec("angle_ref_edge_start", float, 90.0, (0.1, 179.9)),
        "AngleRefEdgeEnd": AttributeSpec("angle_ref_edge_end", float, 90.0, (0.1, 179.9)),
        "AngleOppEdgeStart": AttributeSpec("angle_opp_edge_start", float, 90.0, (0.1, 179.9)),
        "AngleOppEdgeEnd": AttributeSpec("angle_opp_edge_end", float, 90.0, (0.1, 179.9)),
    }

    def volumes_from_params_and_element(self, element):
        """The two volumes above the inclined planes, split at the vertical plane through the ridge line.

        Each is limited at its start and end by a wall which stands perpendicular on its inclined plane, as the figure marks.
        The figure does not define where the walls of the two sides meet above the ridge line if they differ, so they just meet at the split.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        start = Point(self.start_x, self.start_y, -self.start_depth)
        end = start + Vector(self.length, 0.0, 0.0)
        reach = element.blank_length + element.width + element.height + self.length + abs(self.start_x) + abs(self.start_y) + abs(self.start_depth)
        box = Brep.from_box(Box(2.0 * reach, 2.0 * reach, 2.0 * reach, Frame(start, [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))
        to_model = Transformation.from_frame(element.ref_sides[self.ref_side_index])

        volumes = []
        sides = (
            (-1.0, self.inclination_ref_side, self.angle_ref_edge_start, self.angle_ref_edge_end),
            (1.0, self.inclination_opp_side, self.angle_opp_edge_start, self.angle_opp_edge_end),
        )
        for side, inclination, angle_start, angle_end in sides:
            inclination = math.radians(inclination)
            angle_start = math.radians(angle_start)
            angle_end = math.radians(angle_end)
            slope = Vector(0.0, side * math.cos(inclination), -math.sin(inclination))  # in the inclined plane, away from the ridge line
            up = Vector(0.0, side * math.sin(inclination), math.cos(inclination))

            # Brep.trimmed() keeps what is behind the plane
            volume = box.trimmed(Plane(start, up * -1.0)).trimmed(Plane(start, Vector(0.0, -side, 0.0)))
            if self.start_limited:
                volume = volume.trimmed(Plane(start, slope * math.cos(angle_start) - Vector(math.sin(angle_start), 0.0, 0.0)))
            if self.end_limited:
                volume = volume.trimmed(Plane(end, slope * math.cos(angle_end) + Vector(math.sin(angle_end), 0.0, 0.0)))
            volumes.append(volume.transformed(to_model))
        return volumes
