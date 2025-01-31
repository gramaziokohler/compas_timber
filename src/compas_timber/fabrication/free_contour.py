import xml.etree.ElementTree as ET

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
    """Represents a drilling processing.

    Parameters
    ----------
    start_x : float
        The x-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    start_y : float
        The y-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    angle : float
        The rotation angle of the drilling. In degrees. Around the z-axis of the reference side.
    inclination : float
        The inclination angle of the drilling. In degrees. Around the y-axis of the reference side.
    depth_limited : bool, default True
        If True, the drilling depth is limited to `depth`. Otherwise, drilling will go through the element.
    depth : float, default 50.0
        The depth of the drilling. In mm.
    diameter : float, default 20.0
        The diameter of the drilling. In mm.
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
        self.inclination = inclination

    ########################################################################
    # Properties
    ########################################################################

    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element."""
        return {"Name": self.PROCESSING_NAME, "CounterSink": "yes" if self.couter_sink else "no", "ToolID": "0", "Process": "yes", "ToolPosition": self.tool_position, "ReferencePlaneID": "4"}

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

        """
        pline = [pt.copy() for pt in polyline]
        pline = correct_polyline_direction(pline, element.ref_frame.normal, clockwise=True)
        tool_position = AlignmentType.RIGHT if interior else AlignmentType.LEFT # TODO: see if we can have CCW contours. for now only CW.
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
            vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_frame.normal * self.depth* 2.0)
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

    def create_processing(self):
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
        processing_element = ET.Element(
            self.PROCESSING_NAME,
            self.header_attributes,
        )
        contour_element = ET.SubElement(processing_element, "Contour", self.contour_attributes)
        ET.SubElement(contour_element, "StartPoint", BTLxPart.et_point_vals(self.contour_points[0]))
        for pt in self.contour_points[1:]:
            point_element = ET.SubElement(contour_element, "Line")  # TODO: consider implementing arcs. maybe as tuple? (Point,Point)
            point_element.append(ET.Element("EndPoint", BTLxPart.et_point_vals(pt)))
        return processing_element


class FreeCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(FreeCountourParams, self).__init__(instance)

    def as_dict(self):  # don't run super().as_dict() because it will return the default values
        result = {}
        result["header_attributes"] = self._instance.header_attributes
        result["contour_attributes"] = self._instance.contour_attributes
        result["contour_points"] = FreeContour.polyline_to_contour(self._instance.contour_points)
        return result
