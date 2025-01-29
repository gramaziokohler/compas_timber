import math
from re import L

from compas.geometry import Brep
from compas.geometry import Cylinder
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

    PROCESSING_NAME = "Drilling"  # type: ignore

    def __init__(self, start_point, contours, **kwargs):
        super(FreeContour, self).__init__(**kwargs)
        self._start_point = None
        self._contours = None

        self.start_point = start_point
        self.contours = contours

    ########################################################################
    # Properties
    ########################################################################

    @property
    def start_point(self):
        return self._start_point

    @start_point.setter
    def start_point(self, value):
        self._start_point = Point(*value)

    @property
    def contours(self):
        return self._contours

    @contours.setter
    def contours(self, value):
        self._contours = value


    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element.
        CounterSink="yes" ToolID="0" ToolPosition="left" Process="yes" ReferencePlaneID="101" Name="Contour""""
        return {
            "Name": self.PROCESSING_NAME,
            "ToolID":"0",
            "Process": "yes",
            "ToolPosition":AlignmentType.LEFT,
            "ReferencePlaneID": str(self.ref_side_index + 1),
        }


    @property
    def simple_contour_dict(self):
        return SimpleCountourParams(self).as_dict()



    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(cls, polyline, element, ref_side_index=0):
        """Construct a drilling processing from a line and diameter.

        # TODO: change this to point + vector instead of line. line is too fragile, it can be flipped and cause issues.
        # TODO: make a from point alt. constructor that takes a point and a reference side and makes a straight drilling through.

        Parameters
        ----------
        line : :class:`compas.geometry.Line`
            The line on which the drilling is to be made.
        diameter : float
            The diameter of the drilling.
        length : float
            The length (depth?) of the drilling.
        beam : :class:`compas_timber.elements.Beam`
            The beam to drill.

        Returns
        -------
        :class:`compas_timber.fabrication.Drilling`
            The constructed drilling processing.

        """
        frame = element.ref_sides[ref_side_index]
        xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        points = [pt.transformed(xform) for pt in polyline]
        return cls(points[0], polyline[1:], ref_side_index=ref_side_index)


    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
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
        drill_geometry = Brep.from_cylinder(self.cylinder_from_params_and_beam(beam))
        try:
            return geometry - drill_geometry
        except IndexError:
            raise FeatureApplicationError(
                drill_geometry,
                geometry,
                "The drill geometry does not intersect with beam geometry.",
            )


    @staticmethod
    def polyline_to_contour(polyline):
        result = [{"StartPoint": BTLxPart.et_point_vals(polyline[0])}]
        for point in polyline[1:]:
            result.append({"Line": {"EndPoint": BTLxPart.et_point_vals(point)}})



class SimpleCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(SimpleCountourParams, self).__init__(instance)

    def as_dict(self):
        result = super(SimpleCountourParams, self).as_dict()
        result["StartPoint"] = "{:.{prec}f}".format(float(self._instance.start_point), prec=TOL.precision)
        result["Contour"] = self._instance.polyline_to_contour(self._instance.contours)
        return result
