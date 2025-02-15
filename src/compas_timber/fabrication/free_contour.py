from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Transformation

from compas_timber.utils import correct_polyline_direction

from .btlx import AlignmentType
from .btlx import BTLxPart
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams


class FreeContour(BTLxProcessing):
    """Represents a free contour processing.

    Parameters
    ----------
    contour_points : list of :class:`compas.geometry.Point`
        The points of the contour.
    depth : float
        The depth of the contour.
    couter_sink : bool, optional
        If True, the contour is a counter sink. Default is False.
    tool_position : str, optional
        The position of the tool. Default is "left".
    depth_bounded : bool, optional
        If True, the depth is bounded. Default is False, meaning the machining will cut all the way through the element.
    inclination : float, optional
        The inclination of the contour. Default is 0. This is not yet implemented.

    """

    # TODO: add __data__

    PROCESSING_NAME = "FreeContour"  # type: ignore

    def __init__(self, contour_points, depth, couter_sink=False, tool_position=AlignmentType.LEFT, depth_bounded=False, inclination=0, **kwargs):
        super(FreeContour, self).__init__(**kwargs)
        self.contour_points = contour_points
        self.depth = depth
        self.couter_sink = couter_sink
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
        data["couter_sink"] = self.couter_sink
        data["tool_position"] = self.tool_position
        data["depth_bounded"] = self.depth_bounded
        data["inclination"] = self.inclination
        return data

    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element."""
        return {
            "Name": self.PROCESSING_NAME,
            "CounterSink": "yes" if self.couter_sink else "no",
            "ToolID": "0",
            "Process": "yes",
            "ToolPosition": self.tool_position,
            "ReferencePlaneID": "4",
        }

    @property
    def contour_attributes(self):
        return {"Depth": str(self.depth), "DepthBounded": "yes" if self.depth_bounded else "no", "Inclination": str(self.inclination)}

    @property
    def params_dict(self):
        return FreeCountourParams(self).as_dict()

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(cls, polyline, element, depth=None, interior=True, ref_side_index=4):
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
        ref_side_index : int, optional
            The reference side index. Default is 4.
        """
        pline = [pt.copy() for pt in polyline]
        pline = correct_polyline_direction(pline, element.ref_frame.normal, clockwise=True)
        tool_position = AlignmentType.RIGHT if interior else AlignmentType.LEFT  # TODO: see if we can have CCW contours. for now only CW.
        couter_sink = True if interior else False

        depth = depth or element.width
        frame = element.ref_frame
        xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        points = [pt.transformed(xform) for pt in pline]
        return cls(points, depth, tool_position=tool_position, couter_sink=couter_sink, ref_side_index=ref_side_index)

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
        if self.tool_position == AlignmentType.RIGHT:  # contour should remove material inside of the contour
            xform = Transformation.from_frame_to_frame(Frame.worldXY(), element.ref_frame)
            pts = [pt.transformed(xform) for pt in self.contour_points]
            pts = correct_polyline_direction(pts, element.ref_frame.normal, clockwise=True)
            vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_frame.normal * self.depth * 2.0)
            vol.translate(element.ref_frame.normal * -self.depth)
            return geometry - vol
        else:
            xform = Transformation.from_frame_to_frame(Frame.worldXY(), element.ref_frame)
            pts = [pt.transformed(xform) for pt in self.contour_points]
            pts = correct_polyline_direction(pts, element.ref_frame.normal, clockwise=True)
            vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_frame.normal * self.depth)
            return geometry & vol

    @staticmethod
    def polyline_to_contour(polyline):
        result = [{"StartPoint": BTLxPart.et_point_vals(polyline[0])}]
        for point in polyline[1:]:
            result.append({"Line": {"EndPoint": BTLxPart.et_point_vals(point)}})
        return result

    def processing_dict(self):
        """Creates a processing element. This method creates the subprocess elements and appends them to the processing element.
        NOTE: moved to BTLxProcessing because some processings are significantly different and need to be overridden.

        Parameters
        ----------
        processing : :class:`~compas_timber.fabrication.btlx.BTLxProcessing`
            The processing object.

        Returns
        -------
        :class:`~xml.etree.ElementTree.Element`
            The processing element.

        """
        # create processing element

        contour_dict = {
            "name": "Contour",
            "attributes": self.contour_attributes,
            "content": [{"name": "StartPoint", "attributes": BTLxPart.et_point_vals(self.contour_points[0])}],
        }
        for pt in self.contour_points[1:]:  # TODO: consider implementing arcs. maybe as tuple? (Point,Point)
            point_dict = {"name": "Line", "attributes": {}, "content": [{"name": "EndPoint", "attributes": BTLxPart.et_point_vals(pt)}]}
            contour_dict["content"].append(point_dict)

        processing_dict = {"name": self.PROCESSING_NAME, "attributes": self.header_attributes, "content": [contour_dict]}
        return processing_dict


class FreeCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(FreeCountourParams, self).__init__(instance)

    def as_dict(self):  # don't run super().as_dict() because it will return the default values
        result = {}
        result["header_attributes"] = self._instance.header_attributes
        result["contour_attributes"] = self._instance.contour_attributes
        result["contour_points"] = FreeContour.polyline_to_contour(self._instance.contour_points)
        return result
