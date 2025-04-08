import math

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.tolerance import Tolerance

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_polyline_clockwise

from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import Contour
from .btlx import DualContour

TOL = Tolerance()


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

    def __init__(self, contour_points, associated_contour=None, depth=None, counter_sink=False, tool_position=AlignmentType.LEFT, depth_bounded=False, inclination=None, **kwargs):
        super(FreeContour, self).__init__(**kwargs)
        self.contour_points = contour_points
        if not (associated_contour or depth):
            raise ValueError("Contour requires either a depth value or an associated_contour (for DualContour).")
        self.associated_contour = associated_contour
        self.depth = depth
        self.counter_sink = counter_sink
        self.tool_position = tool_position
        self.depth_bounded = depth_bounded
        if inclination is not None:
            if isinstance(inclination, (int, float)):
                self.inclination = inclination
            elif not isinstance(inclination, list):
                raise ValueError("Inclination should be a float or a list of floats.")
            elif len(inclination) != len(contour_points) - 1:
                raise ValueError("Inclination should either be a single float or have the same number of values as contour segments.")
            else:
                self.inclination = inclination
        else:
            self.inclination = 0.0

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
    def from_polyline_and_element(cls, polyline, element, depth=None, interior=None, tool_position=None, ref_side_index=None):
        """Construct a Contour processing from a polyline and element.

        Parameters
        ----------
        polyline : list of :class:`compas.geometry.Point`
            The polyline of the contour.
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element.
        depth : float, optional
            The depth of the contour. Default is the thickness of the element.
        interior : bool, optional
            If True, the contour is an interior contour. Default is True.
        tool_position : BTLx.AlignmentType, optional
            The position of the tool. Default is "left".
        ref_side_index : int, optional
            The reference side index. If none is given, the function will try to find the reference side index based on the polyline and element.
        """

        if not ref_side_index:
            ref_side_index = cls.get_ref_face_index(polyline, element)

        ref_side = element.ref_sides[ref_side_index]

        if polyline[0] != polyline[-1]:  # if polyline is not closed
            if tool_position is None:
                raise ValueError("The polyline should be closed or a tool position should be provided.")
            elif interior:
                raise ValueError("Interior polyline must be closed.")
        else:
            if interior:
                if is_polyline_clockwise(polyline, ref_side.normal):
                    tool_position = AlignmentType.RIGHT
                else:
                    tool_position = AlignmentType.LEFT
            else:
                if is_polyline_clockwise(polyline, ref_side.normal):
                    tool_position = AlignmentType.LEFT
                else:
                    tool_position = AlignmentType.RIGHT

        depth = depth or element.width
        xform = Transformation.from_frame_to_frame(ref_side, Frame.worldXY())
        points = [pt.transformed(xform) for pt in polyline]
        return cls(points, depth=depth, tool_position=tool_position, counter_sink=interior, ref_side_index=ref_side_index)

    @classmethod
    def from_polylines_and_element(cls, polylines, element, interior=None, tool_position=None, ref_side_index=None):
        """Construct a Contour processing from a list of polylines and element.

        Parameters
        ----------
        polylines : list of list of :class:`compas.geometry.Point`
            The top and bottome polylines of the contour.
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element.
        interior : bool, optional
            If True, the contour is an interior contour. Default is None.
        tool_position : BTLx.AlignmentType, optional
            The position of the tool. Default is None.
        ref_side_index : int, optional
            The reference side index. If none is given, the function will try to find the reference side index based on the polylines and element.
        """

        if len(polylines) != 2:
            raise ValueError("Two polylines are expected.")

        if len(polylines[0]) != len(polylines[1]):
            raise ValueError("The top and bottom polylines should have the same number of points.")

        if not ref_side_index:
            ref_side_index = cls.get_ref_face_index(polylines[0], element)

        ref_side = element.ref_sides[ref_side_index]

        if polylines[0][0] != polylines[0][-1]:  # if polyline is not closed
            if tool_position is None:
                raise ValueError("The polyline should be closed or a tool position should be provided.")
            elif interior:
                raise ValueError("Interior polyline must be closed.")
        else:
            if interior:
                if is_polyline_clockwise(polylines[0], ref_side.normal):
                    tool_position = AlignmentType.RIGHT
                else:
                    tool_position = AlignmentType.LEFT
            else:
                if is_polyline_clockwise(polylines[0], ref_side.normal):
                    tool_position = AlignmentType.LEFT
                else:
                    tool_position = AlignmentType.RIGHT

        if not cls.are_all_segments_parallel(polylines[0], polylines[1]):  # use DualContour
            xform = Transformation.from_frame_to_frame(ref_side, Frame.worldXY())
            points_principal = [pt.transformed(xform) for pt in polylines[0]]
            points_associated = [pt.transformed(xform) for pt in polylines[1]]
            return cls(points_principal, points_associated, counter_sink=interior, tool_position=tool_position, ref_side_index=ref_side_index)

        else:  # use Contour with inclination
            inclinations = []
            for top_line, bottom_line in zip(Polyline(polylines[0]).lines, Polyline(polylines[1]).lines):
                cp = bottom_line.closest_point(top_line.start)
                inclination = angle_vectors_signed(Vector.from_start_end(top_line.start, cp), -ref_side.normal, -top_line.direction, deg=True)
                inclinations.append(inclination)
            if len(set(inclinations)) == 1:
                inclinations = inclinations[0]  # remove duplicates
            depth = distance_point_plane(polylines[1][0], Plane.from_frame(ref_side))
            xform = Transformation.from_frame_to_frame(ref_side, Frame.worldXY())
            points = [pt.transformed(xform) for pt in polylines[0]]
            return cls(points, depth=depth, counter_sink=interior, tool_position=tool_position, ref_side_index=ref_side_index, inclination=inclinations)

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

    @staticmethod
    def get_ref_face_index(contour_points, element):
        curve_frame = Frame.from_points(contour_points[0], contour_points[1], contour_points[-2])
        for i, ref_side in enumerate(element.ref_sides):
            if TOL.is_zero(distance_point_plane(contour_points[0], Plane.from_frame(ref_side)), tol=1e-6) and TOL.is_zero(
                angle_vectors(ref_side.normal, curve_frame.zaxis, deg=True) % 180.0, 1e-6
            ):
                return i
        raise ValueError("The contour does not lay on one of the reference sides of the element.")

    @staticmethod
    def are_all_segments_parallel(polyline_a, polyline_b):
        for top_line, bottom_line in zip(Polyline(polyline_a).lines, Polyline(polyline_b).lines):
            if not TOL.is_zero(angle_vectors(top_line.direction, bottom_line.direction) % math.pi, tol=1e-6):
                return False
        return True

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
        ref_side = element.ref_sides[self.ref_side_index]
        xform = Transformation.from_frame_to_frame(Frame.worldXY(), ref_side)
        pts = [pt.transformed(xform) for pt in self.contour_points]
        pts = correct_polyline_direction(pts, ref_side.normal, clockwise=True)
        vol = Brep.from_extrusion(NurbsCurve.from_points(pts, degree=1), ref_side.normal * self.depth * 2.0)
        vol.translate(ref_side.normal * -self.depth)

        if self.counter_sink:  # contour should remove material inside of the contour
            return geometry - vol
        else:
            return geometry & vol


class FreeCountourParams(BTLxProcessingParams):
    def __init__(self, instance):
        # type: (FreeContour) -> None
        super(FreeCountourParams, self).__init__(instance)

    def as_dict(self):
        if not self._instance.associated_contour:
            contour_line = Polyline(self._instance.contour_points)
            return {"Contour": Contour(contour_line, depth=self._instance.depth, depth_bounded=self._instance.depth_bounded, inclination=self._instance.inclination)}
        else:
            contour_line = Polyline(self._instance.contour_points)
            associated_contour_line = Polyline(self._instance.associated_contour)
            return {"Contour": DualContour(contour_line, associated_contour_line, depth_bounded=self._instance.depth_bounded)}

    @property
    def header_attributes(self):
        """Return the attributes to be included in the XML element."""
        return {
            "Name": self._instance.PROCESSING_NAME,
            "CounterSink": "yes" if self._instance.counter_sink else "no",
            "ToolID": "0",
            "Process": "yes",
            "ToolPosition": self._instance.tool_position,
            "ReferencePlaneID": str(self._instance.ref_side_index + 1),
        }
