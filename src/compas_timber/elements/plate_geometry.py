from typing import Optional

from compas.data import Data
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.tolerance import TOL
from compas_brep import Brep

from compas_timber.geometry import brep_from_outlines
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import move_polyline_segment_to_plane


class PlateGeometry(Data):
    """
    A class to represent plate-like objects (plate, panel, etc.) defined by polylines on top and bottom faces of shape.

    Parameters
    ----------
    local_outline_a : :class:`~compas.geometry.Polyline`
        The principal outline of the plate in local space (projected on worldXY, starting at origin).
    local_outline_b : :class:`~compas.geometry.Polyline`
        The associated outline of the plate in local space. Must have the same number of points as outline_a,
        be parallel to outline_a, and be offset in the +Z direction.
    frame : :class:`~compas.geometry.Frame`, optional
        The local coordinate frame of the plate in global space. Defaults to worldXY.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The local coordinate frame of the plate in global space.
    length : float
        Length of the plate along the local x-axis.
    width : float
        Width of the plate along the local y-axis.
    thickness : float
        Thickness of the plate along the local z-axis.
    outline_a : :class:`~compas.geometry.Polyline`
        The principal outline of the plate in local space (mutable, affected by edge extensions).
    outline_b : :class:`~compas.geometry.Polyline`
        The associated outline of the plate in local space (mutable, affected by edge extensions).
    outlines : tuple[:class:`~compas.geometry.Polyline`, :class:`~compas.geometry.Polyline`]
        A tuple containing both outline_a and outline_b.
    edge_planes : list[:class:`~compas.geometry.Frame`]
        Frames representing the edge planes of the plate.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.

    """

    @property
    def __data__(self):
        return {
            "local_outline_a": self._original_outlines[0],
            "local_outline_b": self._original_outlines[1],
            "frame": self.frame,
            "length": self.length,
            "width": self.width,
            "thickness": self.thickness,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["local_outline_a"], data["local_outline_b"], data["frame"])

    def __init__(self, local_outline_a: Polyline, local_outline_b: Polyline, frame: Optional[Frame] = None, **kwargs):
        super().__init__(**kwargs)
        self._check_outlines(local_outline_a, local_outline_b)
        box = Box.from_points(local_outline_a.points + local_outline_b.points)
        self.frame = frame if frame is not None else Frame.worldXY()
        self.length = box.xsize
        self.width = box.ysize
        self.thickness = box.zsize
        self._original_outlines = None
        self._mutable_outlines = None
        self._original_edge_planes = {}
        self._set_original_attributes(local_outline_a, local_outline_b)
        self._extension_planes = {}

    def __repr__(self):
        # type: () -> str
        return "PlateGeometry(outline_a={!r}, outline_b={!r})".format(self.outline_a, self.outline_b)

    def __str__(self):
        return "PlateGeometry {}, {} ".format(self.outline_a, self.outline_b)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def outline_a(self) -> Polyline:
        return self._mutable_outlines[0]

    @property
    def outline_b(self) -> Polyline:
        return self._mutable_outlines[1]

    @property
    def edge_planes(self) -> dict[int, Plane]:
        _edge_planes = {}
        for i in range(len(self._mutable_outlines[0]) - 1):
            _edge_planes[i] = self._extension_planes.get(i) or self._original_edge_planes[i]
        return _edge_planes

    def compute_aabb(self, inflate: float = 0.0) -> Box:
        box = Box.from_points(self._mutable_outlines[0].points + self._mutable_outlines[1].points)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def _set_original_attributes(self, outline_a, outline_b) -> None:
        self._original_outlines = (outline_a, outline_b)
        self._mutable_outlines = (outline_a.copy(), outline_b.copy())

        for edge_index in range(len(outline_a) - 1):
            plane = Plane.from_points([outline_a[edge_index], outline_a[edge_index + 1], outline_b[edge_index]])
            self._original_edge_planes[edge_index] = self._corrected_edge_plane(edge_index, plane)

    def set_extension_plane(self, edge_index: int, plane: Plane) -> None:
        """Sets an extension plane for a specific edge of the plate. This is called by plate joints."""
        self._extension_planes[edge_index] = self._corrected_edge_plane(edge_index, plane)

    def _corrected_edge_plane(self, edge_index, plane):
        if dot_vectors(plane.normal, get_polyline_segment_perpendicular_vector(self._mutable_outlines[0], edge_index)) < 0:
            return Plane(plane.point, -plane.normal)
        return plane

    def apply_edge_extensions(self) -> None:
        """adjusts segments of the outlines to lay on the edge planes created by plate joints."""
        # TODO: Add an optional edge_index argument to only apply a specific edge extension for performance?
        for edge_index, plane in self.edge_planes.items():
            for polyline in self._mutable_outlines:
                move_polyline_segment_to_plane(polyline, edge_index, plane)

    def remove_blank_extension(self, edge_index: Optional[int] = None):
        """Reverts any extension plane for the given edge index to the original and adjusts that ."""
        if edge_index is None:
            # reset all edges to original
            self.reset()
            return
        if edge_index > len(self._mutable_outlines[0]) - 1:
            raise ValueError("Edge index out of range.")
        if edge_index in self._extension_planes:
            # delete the externally set extension plane
            del self._extension_planes[edge_index]
        for pl in self._mutable_outlines:
            # revert the polyline segment to the original edge plane
            move_polyline_segment_to_plane(pl, edge_index, self._original_edge_planes[edge_index])

    def reset(self):
        """Resets the element outlines to their initial state."""
        self._mutable_outlines = (self._original_outlines[0].copy(), self._original_outlines[1].copy())
        self._extension_planes = {}

    # ==========================================================================
    #  Implementation of abstract methods
    # ==========================================================================

    def compute_shape(self) -> Brep:
        """The shape of the plate before other features area applied.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The shape of the element.

        """
        self.apply_edge_extensions()
        plate_geo = brep_from_outlines(self.outline_a, self.outline_b)

        return plate_geo

    # ==========================================================================
    #  class methods
    # ==========================================================================

    @classmethod
    def from_global_outlines(cls, outline_a: Polyline, outline_b: Polyline, orientation: Optional[Vector] = None) -> "PlateGeometry":
        """Creates a PlateGeometry from two polylines in global (world) space.

        Computes the local frame and transforms the outlines into the plate's local coordinate system.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            Principal outline of the plate in global space.
        outline_b : :class:`~compas.geometry.Polyline`
            Associated outline of the plate in global space. Must be parallel to outline_a
            and offset in the plate's normal direction.
        orientation : :class:`~compas.geometry.Vector`, optional
            A vector that controls the direction of the local coordinate frame.
            When provided, the vector is projected onto the outline plane and used to define
            the local y-axis direction, overriding the frame derived automatically from the
            outline geometry. If ``None``, the frame is determined from the outline.

        Returns
        -------
        :class:`PlateGeometry`
        """
        # get 3 non-colinear points
        pt_c = None
        vector_a = Vector.from_start_end(outline_a[0], outline_a[1])
        for pt in outline_a.points[-1:1:-1]:  # walk bakwards along outline_a.points
            vector_b = Vector.from_start_end(outline_a[0], pt)
            if not TOL.is_allclose(cross_vectors(vector_a, vector_b), [0, 0, 0]):  # cross_vectors returns [0,0,0] for parallel vectors
                pt_c = pt
        if not pt_c:
            raise ValueError("outline_a appears to only have colinear points")

        # get initial frame for rebasing to XY-plane
        frame = Frame.from_points(outline_a[0], outline_a[1], pt_c)

        if orientation:
            orientation = cross_vectors(cross_vectors(orientation, frame.normal), frame.normal)  # project to `frame`
            frame = Frame(outline_a[0], cross_vectors(orientation, frame.normal), orientation)  # create new frame based on orientation

        if dot_vectors(Vector.from_start_end(outline_a[0], outline_b[0]), frame.normal) < 0:
            frame = Frame(frame.point, frame.yaxis, frame.xaxis)  # flip frame if outline_b in -z space
        transform_to_world_xy = Transformation.from_frame_to_frame(frame, Frame.worldXY())

        # move polylines to XY
        rebased_pline_a = Polyline([pt.transformed(transform_to_world_xy) for pt in outline_a.points])
        rebased_pline_b = Polyline([pt.transformed(transform_to_world_xy) for pt in outline_b.points])
        # TODO: rebasing to positive XY space (code below) shouldn't be strictly necessary.
        box = Box.from_points(rebased_pline_a.points + rebased_pline_b.points)
        frame = Frame(box.points[0], Vector(1, 0, 0), Vector(0, 1, 0))  # frame at bounding box corner
        frame.transform(transform_to_world_xy.inverse())
        vector_to_xy = Vector.from_start_end(box.points[0], Point(0, 0, 0))
        # move polylines to positive XY space
        local_outline_a = Polyline([pt.translated(vector_to_xy) for pt in rebased_pline_a.points])
        local_outline_b = Polyline([pt.translated(vector_to_xy) for pt in rebased_pline_b.points])
        return cls(local_outline_a, local_outline_b, frame)

    @classmethod
    def from_frame_and_dims(cls, frame: Frame, length: float, width: float, thickness: float) -> "PlateGeometry":
        """Creates a PlateGeometry with a rectangular outline from a frame and dimensions.

        Parameters
        ----------
        frame : :class:`~compas.geometry.Frame`
            The local coordinate frame of the plate in global space.
        length : float
            Length of the plate along the frame's x-axis.
        width : float
            Width of the plate along the frame's y-axis.
        thickness : float
            Thickness of the plate along the frame's z-axis.

        Returns
        -------
        :class:`PlateGeometry`
        """
        local_outline_a = Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        return cls(local_outline_a, local_outline_b, frame)

    # ==========================================================================
    #  static methods
    # ==========================================================================

    @staticmethod
    def _check_outlines(outline_a: Polyline, outline_b: Polyline) -> None:
        # type: (Polyline, Polyline) -> None
        """Checks if the outlines are valid. Outlines should already be at the plate's local frame.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A line representing the principal outline of this plate.
        outline_b : :class:`~compas.geometry.Polyline`
            A line representing the associated outline of this plate.

        raises
        ------
        ValueError if the outlines are not valid.

        """
        if not TOL.is_allclose(outline_a[0], outline_a[-1]):
            raise ValueError("The outline_a is not closed.")
        if not TOL.is_allclose(outline_b[0], outline_b[-1]):
            raise ValueError("The outline_b is not closed.")
        if len(outline_a) != len(outline_b):
            raise ValueError("The outlines must have the same number of points.")
        # check if outline_a is on the XY-plane (all z-coordinates must be 0)
        if not all(TOL.is_close(p[2], 0) for p in outline_a.points):
            raise ValueError("outline_a must lie on the XY-plane (all Z-coordinates must be 0).")
        # check if outline_b is planar and parallel to outline_a
        if not all(TOL.is_close(p[2], outline_b[0][2]) for p in outline_b.points):
            raise ValueError("Outline_b must be planar and parallel to outline_a.")
