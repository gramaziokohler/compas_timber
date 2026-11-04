import math

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polygon
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import ParametricProcessing


class ChamferExitType(object):
    """Enum for the shape of the ends of a limited :class:`Chamfer`.

    Attributes
    ----------
    ORTHOGONAL : literal("orthogonal")
        The chamfer ends in a face perpendicular to the edge.
    ANGULAR : literal("angular")
        The chamfer runs out in a sloped face.
    ROUND : literal("round")
        The chamfer runs out in a rounded face.
    """

    ORTHOGONAL = "orthogonal"
    ANGULAR = "angular"
    ROUND = "round"


class Chamfer(ParametricProcessing):
    """Chamfers the long edges of an element at 45 degrees.

    This processing has no reference side: `start_x` is measured from the start of the element and the edges are named after the sides they join.

    Parameters
    ----------
    start_x : float
        Distance from the start of the element to the start of the chamfer. Also the reference of `length`.
    start_limited : bool
        If True the chamfer starts at `start_x`, otherwise it runs through the start of the element.
    end_limited : bool
        If True the chamfer ends at `start_x` + `length`, otherwise it runs through the end of the element.
    length : float
        Length of the chamfer, including the exits.
    depth : float
        Size of the chamfer, measured along each of the two sides.
    chamfer_edge_12 : bool
        If True the edge between reference sides 1 and 2 is chamfered.
    chamfer_edge_23 : bool
        If True the edge between reference sides 2 and 3 is chamfered.
    chamfer_edge_34 : bool
        If True the edge between reference sides 3 and 4 is chamfered.
    chamfer_edge_41 : bool
        If True the edge between reference sides 4 and 1 is chamfered.
    chamfer_exit : str
        The shape of the limited ends of the chamfer, see :class:`ChamferExitType`.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "Chamfer"  # type: ignore
    HAS_REFERENCE_PLANE = False
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartLimited": AttributeSpec("start_limited", bool, False),
        "EndLimited": AttributeSpec("end_limited", bool, False),
        "Length": AttributeSpec("length", float, 0.0, (0.0, 100000.0), scales=True),
        "Depth": AttributeSpec("depth", float, 1.0, (0.0, 100.0), scales=True),
        "ChamferEdge12": AttributeSpec("chamfer_edge_12", bool, True),
        "ChamferEdge23": AttributeSpec("chamfer_edge_23", bool, True),
        "ChamferEdge34": AttributeSpec("chamfer_edge_34", bool, True),
        "ChamferEdge41": AttributeSpec("chamfer_edge_41", bool, True),
        "ChamferExit": AttributeSpec("chamfer_exit", str, ChamferExitType.ORTHOGONAL, choices=(ChamferExitType.ORTHOGONAL, ChamferExitType.ANGULAR, ChamferExitType.ROUND)),
    }

    def _exit_profile(self, height):
        """(distance along the edge, height above the edge) of the exit, from its tip on the edge to the full height of the chamfer."""
        if self.chamfer_exit == ChamferExitType.ANGULAR:
            return [(0.0, 0.0), (height, height)]
        if self.chamfer_exit == ChamferExitType.ROUND:
            # shortcut: a quarter circle of 16 segments, the extrusion takes a polygon. Upgrade if chamfers get large enough to see it
            angles = [0.5 * math.pi * i / 16 for i in range(17)]
            return [(height * (1.0 - math.cos(angle)), height * math.sin(angle)) for angle in angles]
        return [(0.0, height)]

    def volumes_from_params_and_element(self, element):
        """The chamfers as prisms, one per edge.

        The profile of a prism lies in the plane through the edge and the bisector of its two sides, and it is extruded across the edge.
        Only the part up to the chamfer's height is in the element, so this makes the triangular section without building it,
        and an exit in the profile is an exit on both sides.

        The figure gives no measure for the exits. They are taken as long as the height of the chamfer, which makes the angular exit slope at 45 degrees.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the limited chamfer is too short for its exits.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        height = self.depth / math.sqrt(2.0)
        margin = element.width + element.height

        exit_profile = self._exit_profile(height)
        x_end = self.start_x + self.length
        start = [(self.start_x + x, y) for x, y in exit_profile] if self.start_limited else [(-margin, height)]
        end = [(x_end - x, y) for x, y in reversed(exit_profile)] if self.end_limited else [(element.blank_length + margin, height)]
        if end[0][0] <= start[-1][0]:
            raise ValueError("The Chamfer is too short for its exits.")
        profile = [(start[0][0], -margin)] + start + end + [(end[-1][0], -margin)]

        volumes = []
        edges = (self.chamfer_edge_12, self.chamfer_edge_23, self.chamfer_edge_34, self.chamfer_edge_41)
        for ref_side, is_chamfered in zip(element.ref_sides, edges):
            if is_chamfered:
                # the reference edge of a side is its edge to the next side
                frame = Frame(ref_side.point, ref_side.xaxis, ref_side.yaxis - ref_side.zaxis)
                polygon = Polygon([frame.to_world_coordinates(Point(x, y, -margin)) for x, y in profile])
                volumes.append(Brep.from_extrusion(polygon, frame.zaxis * 2.0 * margin))
        return volumes
