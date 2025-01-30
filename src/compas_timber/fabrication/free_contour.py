import math
import xml.etree.ElementTree as ET

from compas.geometry import Brep
from compas.geometry import NurbsCurve
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_segment_plane
from compas.geometry import is_point_behind_plane
from compas.geometry import is_point_in_polyhedron
from compas.geometry import project_point_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import correct_polyline_direction

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import BTLxPart
from .btlx import AlignmentType


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

    def __init__(self, contour_points, depth, couter_sink = False, tool_position = AlignmentType.LEFT, depth_bounded = False, inclination = 0, **kwargs):
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
        return {
            "Name": self.PROCESSING_NAME,
            "CounterSink": "no",
            "ToolID":"0",
            "Process": "yes",
            "ToolPosition":self.tool_position,
            "ReferencePlaneID": "4"
        }


    @property
    def params_dict(self):
        print("params_dict", FreeCountourParams(self).as_dict())
        return FreeCountourParams(self).as_dict()


    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(cls, polyline, element, depth = None, interior=True, ref_side_index=4):
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
        pline = correct_polyline_direction(pline, element.ref_frame.normal)
        tool_position = AlignmentType.LEFT if interior else AlignmentType.RIGHT
        couter_sink = True if interior else False

        depth = depth or element.width
        frame = element.ref_frame
        xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        points = [pt.transformed(xform) for pt in pline]
        return cls(points, depth, tool_position = tool_position, couter_sink = couter_sink, ref_side_index=ref_side_index)


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
        if self.tool_position == AlignmentType.LEFT: # contour should remove material inside of the contour
            xform = Transformation.from_frame_to_frame(Frame.worldXY(), element.ref_frame)
            pts = [pt.transformed(xform) for pt in self.contour_points]
            vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_frame.normal * self.depth)
            return geometry - vol
        else:
            volume = Brep.from_box(element.blank)
            xform = Transformation.from_frame_to_frame(Frame.worldXY(), element.ref_frame)
            pts = [pt.transformed(xform) for pt in self.contour_points]
            vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), element.ref_frame.normal * self.depth)
            volume = volume - vol
            return geometry - volume


    @staticmethod
    def polyline_to_contour(polyline):
        result = [{"StartPoint": BTLxPart.et_point_vals(polyline[0])}]
        for point in polyline[1:]:
            result.append({"Line": {"EndPoint": BTLxPart.et_point_vals(point)}})
        print("polyline_to_contour", result)
        return result

    def create_processing(self):
        """Creates a processing element. This method creates the subprocess elements and appends them to the processing element.
        moved to BTLxProcessing because some processings are significantly different and need to be overridden.

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
        # create parameter subelements
        contour_params = {
            "Depth": str(self.depth),
            "DepthBounded": "yes" if self.depth_bounded else "no",
            "Inclination": str(self.inclination)
        }

        contour_element = ET.SubElement(processing_element, "Contour", contour_params)
        ET.SubElement(contour_element, "StartPoint", BTLxPart.et_point_vals(self.contour_points[0]))
        for pt in self.contour_points[1:]:
            point_element = ET.SubElement(contour_element, "Line")
            point_element.append(ET.Element("EndPoint", BTLxPart.et_point_vals(pt)))
        return processing_element



class FreeCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(FreeCountourParams, self).__init__(instance)

    def as_dict(self):
        result = {}
        result["Contour"] = FreeContour.polyline_to_contour(self._instance.contour)
        return result
