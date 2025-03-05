from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Polyline
from compas.geometry import Transformation

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_polyline_clockwise

from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import Contour


class FreeContour(BTLxProcessing):
    """Represents a free contour processing.

    Parameters
    ----------
    contour_points : list of :class:`compas.geometry.Point`
        The points of the contour.
    depth : float
        The depth of the contour.
    counter_sink : bool, optional
        If True, the contour is a counter sink. Default is False.
    tool_position : str, optional
        The position of the tool. Default is "left".
    depth_bounded : bool, optional
        If True, the depth is bounded. Default is False, meaning the machining will cut all the way through the element.
    inclination : float, optional
        The inclination of the contour. Default is 0. This is not yet implemented.

    """

    PROCESSING_NAME = "FreeContour"  # type: ignore

    def __init__(self, contour_points, depth, counter_sink=False, tool_position=AlignmentType.LEFT, depth_bounded=False, inclination=0, **kwargs):
        super(FreeContour, self).__init__(**kwargs)
        self.contour_points = contour_points
        self.depth = depth
        self.counter_sink = counter_sink
        self.tool_position = tool_position
        self.depth_bounded = depth_bounded
        if inclination != 0:
            raise NotImplementedError("Inclination is not yet implemented.")
        self.inclination = inclination

    ########################################################################
    # Properties
    ########################################################################

    @property
    def __data__(self):
        data = super(FreeContour, self).__data__
        data["contour_points"] = self.contour_points
        data["depth"] = self.depth
        data["counter_sink"] = self.counter_sink
        data["tool_position"] = self.tool_position
        data["depth_bounded"] = self.depth_bounded
        data["inclination"] = self.inclination
        return data

    @property
    def params(self):  # TODO: I think this only gets called in tests or once when writing BTLx, but we could consider caching it
        return FreeCountourParams(self)

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(cls, polyline, element, depth=None, interior=True, tool_position=None, ref_side_index=3):
        """Construct a Contour processing from a polyline and element.

        Parameters
        ----------
        polyline : list of :class:`compas.geometry.Point`
            The polyline of the contour.
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element.
        depth : float, optional
            The depth of the contour. Default is the width of the element.
        interior : bool, optional
            If True, the contour is an interior contour. Default is True.
        tool_position : str, optional
            The position of the tool. Default is "left".
        ref_side_index : int, optional
            The reference side index. Default is 3.
        """
        if polyline[0] != polyline[-1]:  # if the polyline is not closed
            if not tool_position:
                raise ValueError("The polyline should be closed or a tool position should be provided.")
            else:
                return cls(polyline, depth, tool_position=tool_position, ref_side_index=ref_side_index)

        if interior:
            counter_sink = True
            if is_polyline_clockwise(polyline, element.ref_sides[ref_side_index].normal):
                tool_position = AlignmentType.RIGHT
            else:
                tool_position = AlignmentType.LEFT
        else:
            counter_sink = False
            if is_polyline_clockwise(polyline, element.ref_sides[ref_side_index].normal):
                tool_position = AlignmentType.LEFT
            else:
                tool_position = AlignmentType.RIGHT

        depth = depth or element.width
        xform = Transformation.from_frame_to_frame(element.ref_frame, Frame.worldXY())
        points = [pt.transformed(xform) for pt in polyline]
        return cls(points, depth, tool_position=tool_position, counter_sink=counter_sink, ref_side_index=ref_side_index)

    @classmethod
    def from_shapes_and_element(cls, polyline, element, depth=None, interior=True, **kwargs):
        """Construct a Contour processing from a list of shapes and element.

        Parameters
        ----------
        shapes : list of :class:`compas.geometry.Shape`
            The shapes of the contour.
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element.
        depth : float, optional
            The depth of the contour. Default is the width of the element.
        interior : bool, optional
            If True, the contour is an interior contour. Default is True.
        """
        return cls.from_polyline_and_element(polyline, element, depth, interior, **kwargs)

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, element):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.
        """
        xform = Transformation.from_frame_to_frame(Frame.worldXY(), element.ref_sides[self.ref_side_index])
        pts = [pt.transformed(xform) for pt in self.contour_points]
        pts = correct_polyline_direction(pts, element.ref_sides[self.ref_side_index].normal, clockwise=True)
        vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_sides[self.ref_side_index].normal * self.depth * 2.0)
        vol.translate(element.ref_sides[self.ref_side_index].normal * -self.depth)

        if self.counter_sink:  # contour should remove material inside of the contour
            return geometry - vol
        else:
            return geometry & vol


class FreeCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        # type: (FreeContour) -> None
        super(FreeCountourParams, self).__init__(instance)

    def as_dict(self):
        contour_line = Polyline(self._instance.contour_points)
        return {"Contour": Contour(contour_line, depth = self._instance.depth, depth_bounded = self._instance.depth_bounded, inclination = self._instance.inclination)}

    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element."""
        return {
            "Name": self._instance.PROCESSING_NAME,
            "CounterSink": "yes" if self._instance.counter_sink else "no",
            "ToolID": "0",
            "Process": "yes",
            "ToolPosition": self._instance.tool_position,
            "ReferencePlaneID": "4",
        }
