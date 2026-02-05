from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

if TYPE_CHECKING:
    from compas.geometry import Polyline  # noqa: F401

    from compas_timber.elements import Beam  # noqa: F401
    from compas_timber.elements import Plate  # noqa: F401
    from compas_timber.elements import TimberElement  # noqa: F401

import math

from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.tolerance import TOL

from compas_timber.utils import is_polyline_clockwise

from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import Contour
from .btlx import DualContour


class FreeContour(BTLxProcessing):
    """Represents a free contour processing.

    Parameters
    ----------
    contour_param_object : :class:`compas_timber.fabrication.btlx.Contour` or :class:`compas_timber.fabrication.btlx.DualContour`
        The contour parameter object.
    tool_id : int, optional
        The tool ID for the processing. Default is 0.
    counter_sink : bool, optional
        If True, the contour is a counter sink. Default is False.
    tool_position : :class:`~compas_timber.fabrication.AlignmentType`
        The position of the tool relative to the beam. Can be 'left', 'center', or 'right'.
    depth_bounded : bool, optional
        If True, the depth is bounded. Default is False, meaning the machining will cut all the way through the element.

    """

    PROCESSING_NAME = "FreeContour"  # type: ignore
    ATTRIBUTE_MAP = {
        "Contour": "contour_param_object",
    }

    def __init__(self, contour_param_object, tool_id=0, counter_sink=False, tool_position=AlignmentType.LEFT, depth_bounded=True, **kwargs):
        super(FreeContour, self).__init__(tool_id=tool_id, counter_sink=counter_sink, tool_position=tool_position, **kwargs)
        self.contour_param_object = contour_param_object
        self.depth_bounded = depth_bounded

    ########################################################################
    # Properties
    ########################################################################

    @property
    def __data__(self):
        data = super(FreeContour, self).__data__
        data["contour_param_object"] = self.contour_param_object
        data["tool_id"] = self.tool_id
        data["counter_sink"] = self.counter_sink
        data["tool_position"] = self.tool_position
        data["depth_bounded"] = self.depth_bounded
        return data

    @property
    def tool_id(self):
        return self._tool_id

    @tool_id.setter
    def tool_id(self, tool_id):
        if not isinstance(tool_id, int):
            raise ValueError("tool_id must be an integer value.")
        self._tool_id = tool_id

    @property
    def counter_sink(self):
        return self._counter_sink

    @counter_sink.setter
    def counter_sink(self, counter_sink):
        if not isinstance(counter_sink, bool):
            raise ValueError("counter_sink must be a boolean value.")
        self._counter_sink = counter_sink

    @property
    def tool_position(self):
        return self._tool_position

    @tool_position.setter
    def tool_position(self, tool_position):
        if tool_position not in [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT]:
            raise ValueError("tool_position must be one of 'left', 'center', or 'right'.")
        self._tool_position = tool_position

    @property
    def depth_bounded(self):
        return self._depth_bounded

    @depth_bounded.setter
    def depth_bounded(self, depth_bounded):
        if not isinstance(depth_bounded, bool):
            raise ValueError("depth_bounded must be a boolean value.")
        self._depth_bounded = depth_bounded

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_polyline_and_element(
        cls,
        polyline: Polyline,
        element: TimberElement,
        depth: Optional[float] = None,
        interior: Optional[bool] = False,
        tool_position: Optional[str] = None,
        ref_side_index: Optional[int] = None,
        **kwargs,
    ):
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
        # get_dimensions_relative_to_side [0] returns element dimension normal to ref_side
        depth = depth or element.get_dimensions_relative_to_side(ref_side_index)[0]
        transformed_polyline = polyline.transformed(Transformation.from_frame(ref_side).inverse())
        contour = Contour(transformed_polyline, depth=depth, inclination=[0.0])
        return cls(contour, tool_position=tool_position, counter_sink=interior, ref_side_index=ref_side_index, **kwargs)

    @classmethod
    def from_top_bottom_and_elements(cls, top_polyline, bottom_polyline, element, interior=False, tool_position=None, ref_side_index=None, **kwargs):
        # type: (Polyline, Polyline, Union[Plate, Beam], bool, str | None, int | None, dict) -> FreeContour
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
        tool_position = cls.parse_tool_position(top_polyline, ref_side, interior, tool_position)
        transformation_to_local = Transformation.from_frame(ref_side).inverse()

        top_polyline = top_polyline.transformed(transformation_to_local)
        bottom_polyline = bottom_polyline.transformed(transformation_to_local)
        if not cls.are_all_segments_parallel(top_polyline, bottom_polyline):  # use DualContour
            contour = DualContour(top_polyline, bottom_polyline)
        else:  # use Contour with inclination
            inclinations = []
            for top_line, bottom_line in zip(top_polyline.lines, bottom_polyline.lines):
                cp = bottom_line.closest_point(top_line.start)
                inclinations.append(round(angle_vectors_signed(Vector.from_start_end(top_line.start, cp), Vector(0, 0, -1), -top_line.direction, deg=True), 6))
            if len(set(inclinations)) == 1:
                inclinations = [inclinations[0]]  # all inclinations are the same, set one global inclination for FreeContour processing
            # bottom polyline is parallel to ref_side. Use Z value of first point to calculate depth
            depth = -bottom_polyline[0][2]
            contour = Contour(top_polyline, depth=depth, inclination=inclinations)

        return cls(contour, counter_sink=interior, tool_position=tool_position, ref_side_index=ref_side_index, **kwargs)  # type: ignore

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
        # type: (Polyline, Union[Plate, Beam]) -> int
        curve_frame = Frame.from_points(contour_points[0], contour_points[1], contour_points[-2])
        for i, ref_side in enumerate(element.ref_sides):
            distance = distance_point_plane(contour_points[0], Plane.from_frame(ref_side))
            if TOL.is_zero(distance, tol=1e-6):
                angle = angle_vectors(ref_side.normal, curve_frame.zaxis, deg=True)
                if TOL.is_zero(angle, 1e-3) or TOL.is_zero(angle - 180.0, 1e-3):
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

        vol = self.contour_param_object.to_brep()
        # contour is defined in the ref_side local frame, need to transform first to global then to element local, where geometry is created
        transformation_ref_side_to_local = element.modeltransformation.inverse() * Transformation.from_frame(element.ref_sides[self.ref_side_index])
        vol.transform(transformation_ref_side_to_local)
        if self.counter_sink:  # contour should remove material inside of the contour
            return geometry - vol
        else:
            return geometry & vol

    def scale(self, factor):
        """Scale the parameters of this processing by a given factor.

        Note
        ----
        Only distances are scaled, angles remain unchanged.

        Parameters
        ----------
        factor : float
            The scaling factor. A value of 1.0 means no scaling, while a value of 2.0 means doubling the size.

        """
        self.contour_param_object.scale(factor)
