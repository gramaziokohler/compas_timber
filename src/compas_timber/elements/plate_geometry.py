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
from compas.geometry import cross_vectors
from compas.tolerance import TOL
from compas_model.elements import reset_computed

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import move_polyline_segment_to_plane
from compas_timber.utils import polyline_from_brep_loop

class PlateGeometry(object):
    """
    A class to represent plate-like objects (plate, slab, etc.) defined by polylines on top and bottom faces of shape.

    Parameters
    ----------
    local_outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate. This should be declared in the local frame of the plate, aka projected on worldXY.
    local_outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should be declared in the local frame of the plate and have the same number of points as outline_a.
        Must be parallel to outline_a. Must be in the +Z direction of the frame.

    Attributes
    ----------
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate in parent space.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate in parent space.
    outlines : tuple[:class:`~compas.geometry.Polyline`, :class:`~compas.geometry.Polyline`]
        A tuple containing both outline_a and outline_b.
    thickness : float
        Thickness of the plate (same as height).
    planes : tuple[:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`]
        The top and bottom planes of the plate.
    normal : :class:`~compas.geometry.Vector`
        Normal vector of the plate.
    edge_planes : list[:class:`~compas.geometry.Frame`]
        Frames representing the edge planes of the plate.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.
    interfaces : list
        List of interfaces associated with this plate.

    """

    @property
    def __data__(self):
        data = {"local_outline_a": self._original_outlines[0], "local_outline_b": self._original_outlines[1]}
        return data

    def __init__(self, local_outline_a, local_outline_b):
        self._original_outlines = (local_outline_a, local_outline_b)
        self._mutable_outlines = (local_outline_a.copy(), local_outline_b.copy())
        self._edge_frames = {}

        self._planes = None
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
    def outlines(self):
        return (self.outline_a, self.outline_b)

    @property
    def outline_a(self):
        return self._mutable_outlines[0].transformed(self.modeltransformation)

    @property
    def outline_b(self):
        return self._mutable_outlines[1].transformed(self.modeltransformation)

    @property
    def thickness(self):
        return self.height

    @property
    def planes(self):
        if not self._planes:
            planes = (Plane.worldXY(), Plane(Point(0, 0, self.thickness), Vector(0, 0, 1)))
            self._planes = (planes[0].transformed(self.modeltransformation), planes[1].transformed(self.modeltransformation))
        return self._planes

    @property
    def normal(self):
        return Vector(0, 0, 1).transformed(self.modeltransformation)

    @property
    def local_outlines(self):
        return self._mutable_outlines

    @property
    def edge_planes(self):
        _edge_planes = {}
        for i in range(len(self._mutable_outlines[0]) - 1):
            plane = self._extension_planes.get(i, None)
            if not plane:
                plane = Plane.from_points([self._mutable_outlines[0][i], self._mutable_outlines[0][i + 1], self._mutable_outlines[1][i]])
                plane = self._corrected_edge_plane(i, plane)
            _edge_planes[i] = plane
        return _edge_planes

    def set_extension_plane(self, edge_index, plane):
        """Sets an extension plane for a specific edge of the plate. This is called by plate joints."""
        self._extension_planes[edge_index] = self._corrected_edge_plane(edge_index, plane)

    def _corrected_edge_plane(self, edge_index, plane):
        if dot_vectors(plane.normal, get_polyline_segment_perpendicular_vector(self._mutable_outlines[0], edge_index)) < 0:
            return Plane(plane.point, -plane.normal)
        return plane

    def apply_edge_extensions(self):
        """adjusts segments of the outlines to lay on the edge planes created by plate joints."""
        for edge_index, plane in self._extension_planes.items():
            for polyline in self._mutable_outlines:
                move_polyline_segment_to_plane(polyline, edge_index, plane)

    def remove_blank_extension(self, edge_index=None):
        """Removes any extension plane for the given edge index."""
        if edge_index is None:
            self._extension_planes = {}
        elif edge_index in self._extension_planes:
            del self._extension_planes[edge_index]

    @reset_computed
    def reset(self):
        """Resets the element outlines to their initial state."""
        self._mutable_outlines = (self._original_outlines[0].copy(), self._original_outlines[1].copy())
        self._edge_frames = {}

    # ==========================================================================
    # Alternate constructors
    # ==========================================================================

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        raise NotImplementedError("PlateGeometry is an abstract class and cannot be instantiated directly. Please use a subclass such as Plate or Slab.")

    @classmethod
    def from_outline_thickness(cls, outline, thickness, vector=None, openings=None, **kwargs):
        """
        Constructs a PlateGeometry from a polyline outline and a thickness.
        The outline is the top face of the plate_geometry, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the plate geometry.
        thickness : float
            The thickness of the plate geometry.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of polyline openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate geometry with the given outline and thickness.
        """
        # this ensure the plate geometry can always be computed
        # TODO: @obucklin `vector` is never actually used here, at most it is used to determine the direction of the thickness vector which is always calculated from the outline.
        # TODO: is this the intention? should it maybe be replaced with some kind of a boolean flag?
        if TOL.is_zero(thickness):
            thickness = TOL.absolute
        print("in from_outline_thickness:")
        for pt in outline.points:
            print(pt)
        offset_vector = Vector(*cross_vectors(outline[1]-outline[0], outline[-2]-outline[0]))  # gets frame perpendicular to outline
        if vector:
            if vector.dot(offset_vector) < 0:  # if vector is given and points in the opposite direction
                offset_vector = -offset_vector
        elif not is_polyline_clockwise(outline, offset_vector):  # if no vector and outline is not clockwise, flip the offset vector
            offset_vector = -offset_vector
        offset_vector.unitize()
        offset_vector *= thickness
        outline_b = Polyline(outline).translated(offset_vector)
        return cls.from_outlines(outline, outline_b, openings=openings, **kwargs)

    @classmethod
    def from_brep(cls, brep, thickness, vector=None, **kwargs):
        """Creates a plate from a brep.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            The brep of the plate.
        thickness : float
            The thickness of the plate.
        vector : :class:`~compas.geometry.Vector`, optional
            The vector in which the plate is extruded.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.PlateGeometry` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate with the given brep and thickness.
        """

        if len(brep.faces) > 1:
            raise ValueError("Can only use single-face breps to create a Plate. This brep has {}".format(len(brep.faces)))
        face = brep.faces[0]
        outer_polyline = None
        inner_polylines = []
        for loop in face.loops:
            if loop.is_outer:
                outer_polyline = polyline_from_brep_loop(loop)
            else:
                inner_polylines.append(polyline_from_brep_loop(loop))
        return cls.from_outline_thickness(outer_polyline, thickness, vector=vector, openings=inner_polylines, **kwargs)

    # ==========================================================================
    #  Implementation of abstract methods
    # ==========================================================================

    def compute_shape(self):
        # type: () -> compas.geometry.Brep
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
        return plate_geo

    def compute_aabb(self, inflate=0.0):
        # type: (float) -> compas.geometry.Box
        """Computes the Axis Aligned Bounding Box (AABB) of the element.

        Parameters
        ----------
        inflate : float, optional
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the element.

        """
        vertices = self.outline_a.points + self.outline_b.points
        box = Box.from_points(vertices)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """

        obb = Box.from_points(self._mutable_outlines[0].points + self._mutable_outlines[1].points)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        obb.transform(self.modeltransformation)
        return obb

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.obb.to_mesh()

    # ==========================================================================
    #  static methods
    # ==========================================================================

    @staticmethod
    def get_args_from_outlines(outline_a, outline_b):
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
        return {
            "local_outline_a": local_outline_a,
            "local_outline_b": local_outline_b,
            "frame": frame,
            "length": box.xsize,
            "width": box.ysize,
            "thickness": box.zsize,
        }

    @staticmethod
    def _check_outlines(outline_a, outline_b):
        # type: (Polyline, Polyline) -> bool
        """Checks if the outlines are valid. Outlines should already be at the plate's local frame.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A line representing the principal outline of this plate.
        outline_b : :class:`~compas.geometry.Polyline`
            A line representing the associated outline of this plate.

        Returns
        -------
        bool
            True if the outlines are valid, False otherwise.

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
