try:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from compas.geometry import Polyline  # noqa: F401

        from compas_timber.elements import Plate  # noqa: F401
except ImportError:
    pass

import math

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.tolerance import TOL

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_polyline_clockwise

from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import Contour
from .btlx import DualContour


class FreeContour(BTLxProcessing):
    """Represents a free contour processing.

    Parameters
    ----------
    contour_param_object : :class:`compas_timber.fabrication.btlx.Contour` or :class:`compas_timber.fabrication.btlx.DualContour`
        The contour parameter object.
    counter_sink : bool, optional
        If True, the contour is a counter sink. Default is False.
    tool_position : str, optional
        The position of the tool. Default is "left".
    depth_bounded : bool, optional
        If True, the depth is bounded. Default is False, meaning the machining will cut all the way through the element.

    """

    PROCESSING_NAME = "FreeContour"  # type: ignore

    def __init__(self, contour_param_object, counter_sink=False, tool_position=AlignmentType.LEFT, depth_bounded=True, **kwargs):
        super(FreeContour, self).__init__(**kwargs)
        self.contour_param_object = contour_param_object
        self.counter_sink = counter_sink
        self.tool_position = tool_position
        self.depth_bounded = depth_bounded

    ########################################################################
    # Properties
    ########################################################################

    @property
    def __data__(self):
        data = super(FreeContour, self).__data__
        data["contour_param_object"] = self.contour_param_object
        data["counter_sink"] = self.counter_sink
        data["tool_position"] = self.tool_position
        data["depth_bounded"] = self.depth_bounded
        return data

    @property
    def params(self):
        return FreeCountourParams(self)

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(cls, polyline, element, depth=None, interior=False, tool_position=None, ref_side_index=None):
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
            If True, the contour is an interior contour. Default is False.
        tool_position : BTLx.AlignmentType, optional
            The position of the tool. Default is "left".
        ref_side_index : int, optional
            The reference side index. If none is given, the function will try to find the reference side index based on the polyline and element.
        """

        if ref_side_index is None:
            ref_side_index = cls.get_ref_face_index(polyline, element)

        ref_side = element.ref_sides[ref_side_index]
        tool_position = cls.parse_tool_position(polyline, ref_side, interior, tool_position)
        depth = depth or element.width
        transformed_polyline = polyline.transformed(Transformation.from_frame_to_frame(ref_side, Frame.worldXY()))
        contour = Contour(transformed_polyline, depth=depth, inclination=[0.0])
        return cls(contour, tool_position=tool_position, counter_sink=interior, ref_side_index=ref_side_index)

    @classmethod
    def from_top_bottom_and_elements(cls, top_polyline, bottom_polyline, element, interior=False, tool_position=None, ref_side_index=None):
        # type: (Polyline, Polyline, Plate, bool, str | None, int | None) -> FreeContour
        """Construct a Contour processing from a list of polylines and element.

        Parameters
        ----------
        polylines : list of list of :class:`compas.geometry.Point`
            The top and bottome polylines of the contour.
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element.
        interior : bool, optional
            If True, the contour is an interior contour. Default is False.
        tool_position : BTLx.AlignmentType, optional
            The position of the tool. Default is None.
        ref_side_index : int, optional
            The reference side index. If none is given, the function will try to find the reference side index based on the polylines and element.
        """
        if len(top_polyline) != len(bottom_polyline):
            raise ValueError("The top and bottom polylines should have the same number of points.")

        if not ref_side_index:
            ref_side_index = cls.get_ref_face_index(top_polyline, element)

        ref_side = element.ref_sides[ref_side_index]
        xform_to_part_coords = Transformation.from_frame_to_frame(ref_side, Frame.worldXY())
        tool_position = cls.parse_tool_position(top_polyline, ref_side, interior, tool_position)

        if not cls.are_all_segments_parallel(top_polyline, bottom_polyline):  # use DualContour
            points_principal = [pt.transformed(xform_to_part_coords) for pt in top_polyline]
            points_associated = [pt.transformed(xform_to_part_coords) for pt in bottom_polyline]
            contour = DualContour(points_principal, points_associated)
        else:  # use Contour with inclination
            inclinations = []
            for top_line, bottom_line in zip(top_polyline.lines, bottom_polyline.lines):
                cp = bottom_line.closest_point(top_line.start)
                inclinations.append(round(angle_vectors_signed(Vector.from_start_end(top_line.start, cp), -ref_side.normal, -top_line.direction, deg=True), 6))
            if len(set(inclinations)) == 1:
                inclinations = [inclinations[0]]  # all inclinations are the same, set one global inclination for FreeContour processing
            depth = distance_point_plane(bottom_polyline[0], Plane.from_frame(ref_side))
            polyline = top_polyline.transformed(xform_to_part_coords)
            contour = Contour(polyline, depth=depth, inclination=inclinations)

        return cls(contour, counter_sink=interior, tool_position=tool_position, ref_side_index=ref_side_index)

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
    def parse_tool_position(polyline, ref_side, interior, tool_position=None):
        # type: (Polyline, Frame, bool, str | None) -> str
        if not polyline.is_closed:  # if polyline is not closed
            if tool_position is None:
                raise ValueError("The polyline should be closed or a tool position should be provided.")
            elif interior:
                raise ValueError("Interior polyline must be closed.")
            else:
                return tool_position
        else:  # if the polyline is closed
            if interior:
                if is_polyline_clockwise(polyline, ref_side.normal):
                    calculated_tool_position = AlignmentType.RIGHT
                else:
                    calculated_tool_position = AlignmentType.LEFT
            else:
                if is_polyline_clockwise(polyline, ref_side.normal):
                    calculated_tool_position = AlignmentType.LEFT
                else:
                    calculated_tool_position = AlignmentType.RIGHT
            if tool_position is None or tool_position == calculated_tool_position:
                return calculated_tool_position
            else:
                raise ValueError("Tool position does not match the contour direction for internal contour.")

    @staticmethod
    def get_ref_face_index(contour_points, element):
        # type: (Polyline, Plate) -> int
        curve_frame = Frame.from_points(contour_points[0], contour_points[1], contour_points[-2])
        for i, ref_side in enumerate(element.ref_sides):
            if TOL.is_zero(distance_point_plane(contour_points[0], Plane.from_frame(ref_side)), tol=1e-6) and TOL.is_zero(
                angle_vectors(ref_side.normal, curve_frame.zaxis, deg=True) % 180.0, 1e-6
            ):
                return i
        raise ValueError("The contour does not lay on one of the reference sides of the element.")

    @staticmethod
    def are_all_segments_parallel(polyline_a, polyline_b):
        for top_line, bottom_line in zip(polyline_a.lines, polyline_b.lines):
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
        # TODO: this doesn't work anymore with the new definition of FreeContour, needs fixing but currently not sure how to do it.
        # TODO: this is only called when there features present other than the Plate's outline (i.e. inner cuts)
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
        return {"Contour": self._instance.contour_param_object}

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
