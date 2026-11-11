from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import ParametricProcessing


class Planing(ParametricProcessing):
    """Planes a layer off the long sides of an element.

    This processing has no reference side: `start_x` is measured from the start of the element.

    Parameters
    ----------
    start_x : float
        Distance from the start of the element to the start of the planing. Also the reference of `length`.
    length : float
        Length of the planing.
    depth : float
        Thickness of the removed layer.
    start_limited : bool
        If True the planing starts at `start_x`, otherwise it runs through the start of the element.
    end_limited : bool
        If True the planing ends at `start_x` + `length`, otherwise it runs through the end of the element.
    plane_side_1 : bool
        If True reference side 1 is planed.
    plane_side_2 : bool
        If True reference side 2 is planed.
    plane_side_3 : bool
        If True reference side 3 is planed.
    plane_side_4 : bool
        If True reference side 4 is planed.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "Planing"  # type: ignore
    HAS_REFERENCE_PLANE = False
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Length": AttributeSpec("length", float, 0.0, (0.0, 100000.0), scales=True),
        "Depth": AttributeSpec("depth", float, 1.0, (0.0, 50.0), scales=True),
        "StartLimited": AttributeSpec("start_limited", bool, False),
        "EndLimited": AttributeSpec("end_limited", bool, False),
        "PlaneSide1": AttributeSpec("plane_side_1", bool, True),
        "PlaneSide2": AttributeSpec("plane_side_2", bool, True),
        "PlaneSide3": AttributeSpec("plane_side_3", bool, True),
        "PlaneSide4": AttributeSpec("plane_side_4", bool, True),
    }

    def volumes_from_params_and_element(self, element):
        """The removed layers, one per planed side, oversized past the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        margin = element.width + element.height
        x_start = self.start_x if self.start_limited else -margin
        x_end = self.start_x + self.length if self.end_limited else element.blank_length + margin
        if x_end <= x_start:
            return []

        volumes = []
        sides = (self.plane_side_1, self.plane_side_2, self.plane_side_3, self.plane_side_4)
        for index, is_planed in enumerate(sides):
            if is_planed:
                ref_side = element.ref_sides[index]
                width = element.get_dimensions_relative_to_side(index)[0]
                center = ref_side.to_world_coordinates(Point(0.5 * (x_start + x_end), 0.5 * width, 0.5 * (margin - self.depth)))
                box = Box(x_end - x_start, width + 2.0 * margin, margin + self.depth, Frame(center, ref_side.xaxis, ref_side.yaxis))
                volumes.append(Brep.from_box(box))
        return volumes
