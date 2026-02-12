from typing import Optional

from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import closest_point_on_plane
from compas.geometry import dot_vectors
from compas.tolerance import TOL

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import move_polyline_segment_to_plane


class PlateGeometry(Data):
    """
    A class to represent plate-like objects (plate, panel, etc.) defined by polylines on top and bottom faces of shape.

    Parameters
    ----------
    local_outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate. This should be declared in the local frame of the plate, aka projected on worldXY.
    local_outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should be declared in the local frame of the plate and have the same number of points as outline_a.
        Must be parallel to outline_a. Must be in the +Z direction of the frame.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this plate.

    Attributes
    ----------
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate in local space.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate in local space.
    outlines : tuple[:class:`~compas.geometry.Polyline`, :class:`~compas.geometry.Polyline`]
        A tuple containing both outline_a and outline_b.
    edge_planes : list[:class:`~compas.geometry.Frame`]
        Frames representing the edge planes of the plate.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.
    openings : list[:class:`~compas.geometry.Polyline`]
        A list of Polyline objects representing openings in this plate.

    """

    @property
    def __data__(self):
        data = {}
        data["local_outline_a"] = self._original_outlines[0]
        data["local_outline_b"] = self._original_outlines[1]
        data["openings"] = self.openings
        return data

    def __init__(self, local_outline_a, local_outline_b, openings=None, **kwargs):
        super().__init__(**kwargs)
        self._original_outlines = None
        self._mutable_outlines = None
        self._original_edge_planes = {}
        self._set_original_attributes(local_outline_a, local_outline_b)
        self.openings = openings or []
        self._extension_planes = {}

    def __repr__(self):
        # type: () -> str
        return "Plate(outline_a={!r}, outline_b={!r})".format(self.outline_a, self.outline_b)

    def __str__(self):
        return "Plate {}, {} ".format(self.outline_a, self.outline_b)

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
        outline_a = correct_polyline_direction(self._mutable_outlines[0], Vector(0, 0, 1), clockwise=True)
        outline_b = correct_polyline_direction(self._mutable_outlines[1], Vector(0, 0, 1), clockwise=True)
        plate_geo = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (outline_a, outline_b)])
        plate_geo.cap_planar_holes()
        for opening in self.openings:
            if not TOL.is_allclose(opening[0], opening[-1]):
                raise ValueError("Opening polyline is not closed.", opening[0], opening[-1])
            polyline_a = correct_polyline_direction(opening, Vector(0, 0, 1), clockwise=True)
            polyline_b = [closest_point_on_plane(pt, self.planes[1]) for pt in polyline_a.points]
            brep = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (polyline_a, polyline_b)])
            brep.cap_planar_holes()
            plate_geo -= brep
        return plate_geo

    # ==========================================================================
    #  static methods
    # ==========================================================================

    @staticmethod
    def get_args_from_outlines(outline_a: Polyline, outline_b: Polyline, openings: Optional[list[Polyline]] = None):
        """
        Get constructor arguments for the PlateGeometry and subclasses from outlines.
        Outlines and openings are transformed to the local frame of the plate.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            Principal outline of the plate.
        outline_b : :class:`~compas.geometry.Polyline`
            Associated outline of the plate.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            List of opening polylines.

        Returns
        -------
        dict
            Dictionary of constructor arguments containing:
            - local_outline_a (:class:`~compas.geometry.Polyline`)
            - local_outline_b (:class:`~compas.geometry.Polyline`)
            - openings (list[:class:`~compas.geometry.Polyline`]|None)
            - frame (:class:`~compas.geometry.Frame`)
            - length (float)
            - width (float)
            - thickness (float)
        """
        # get frame from outline_a
        frame = Frame.from_points(outline_a[0], outline_a[1], outline_a[-2])
        # flip frame so that outline_b is in the +Z direction
        if dot_vectors(Vector.from_start_end(outline_a[0], outline_b[0]), frame.normal) < 0:
            frame = Frame.from_points(outline_a[0], outline_a[-2], outline_a[1])
        # transform outlines to worldXY
        transform_to_world_xy = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        rebased_pline_a = Polyline([pt.transformed(transform_to_world_xy) for pt in outline_a.points])
        rebased_pline_b = Polyline([pt.transformed(transform_to_world_xy) for pt in outline_b.points])
        # get bounding box to define new frame
        box = Box.from_points(rebased_pline_a.points + rebased_pline_b.points)
        frame = Frame(box.points[0], Vector(1, 0, 0), Vector(0, 1, 0))
        # transform frame back to global space
        frame.transform(transform_to_world_xy.inverse())
        # move outlines to +XY
        vector_to_xy = Vector.from_start_end(box.points[0], Point(0, 0, 0))
        local_outline_a = Polyline([pt.translated(vector_to_xy) for pt in rebased_pline_a.points])
        local_outline_b = Polyline([pt.translated(vector_to_xy) for pt in rebased_pline_b.points])
        PlateGeometry._check_outlines(local_outline_a, local_outline_b)
        openings = [o.transformed(Transformation.from_frame(frame).inverse()) for o in openings] if openings else None
        return {
            "local_outline_a": local_outline_a,
            "local_outline_b": local_outline_b,
            "openings": openings,
            "frame": frame,
            "length": box.xsize,
            "width": box.ysize,
            "thickness": box.zsize,
        }

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
        if all(not TOL.is_close(p[2], 0) for p in outline_a.points):
            raise ValueError("outline_a must be planar. Polyline: {}".format(outline_a))
        if all(not TOL.is_close(p[2], outline_b[0][2]) for p in outline_b.points):
            raise ValueError("Outline_b must be planar and parallel to outline_a.")
