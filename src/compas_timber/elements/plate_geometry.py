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
from compas_model.elements import reset_computed

from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import move_polyline_segment_to_plane


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
    openings : list[:class:`~compas_timber.elements.Opening`], optional
        A list of Opening objects representing openings in this plate.

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
    openings : list[:class:`~compas_timber.elements.Opening`]
        A list of Opening objects representing openings in this plate.

    """

    @property
    def __data__(self):
        data = super(PlateGeometry, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["openings"] = self.openings
        return data

    def __init__(self, local_outline_a, local_outline_b, openings=None):
        self._original_outlines = (local_outline_a, local_outline_b)
        self._mutable_outlines = (local_outline_a.copy(), local_outline_b.copy())
        self._edge_frames = {}

        self._planes = None
        self.openings = openings or []
        self._extension_planes = {}
        self.test = []

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
        """The outlines of the plate.

        Returns
        -------
        tuple[:class:`~compas.geometry.Polyline`, :class:`~compas.geometry.Polyline`]
            A tuple containing outline_a and outline_b.
        """
        return (self.outline_a, self.outline_b)

    @property
    def outline_a(self):
        """The principal outline of the plate.

        Returns
        -------
        :class:`~compas.geometry.Polyline`
            The principal outline of the plate.
        """
        return self._mutable_outlines[0].transformed(Transformation.from_frame(self.frame))

    @property
    def outline_b(self):
        """The associated outline of the plate.

        Returns
        -------
        :class:`~compas.geometry.Polyline`
            The associated outline of the plate.
        """
        return self._mutable_outlines[1].transformed(Transformation.from_frame(self.frame))

    @property
    def thickness(self):
        """The thickness of the plate.

        Returns
        -------
        float
            The thickness of the plate (same as height).
        """
        return self.height

    @property
    def planes(self):
        """The top and bottom planes of the plate.

        Returns
        -------
        tuple[:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`]
            The top and bottom planes of the plate.
        """
        if not self._planes:
            self._planes = (Plane.from_frame(self.frame), Plane.from_frame(self.frame.translated(self.thickness * self.frame.normal)))
        return self._planes

    @property
    def normal(self):
        """Normal vector of the plate."""
        return self.frame.normal

    @property
    def local_outlines(self):
        """Returns the local outlines of the plate."""
        return self._mutable_outlines

    @property
    def edge_planes(self):
        """Frames representing the edge planes of the plate.

        Returns
        -------
        dict:
            A dict of frames representing the edge planes of the plate.
        """
        _edge_planes = {}
        for i in range(len(self._mutable_outlines[0]) - 1):
            frame = self._extension_planes.get(i, None)
            if not frame:
                frame = Frame.from_points(self._mutable_outlines[0][i], self._mutable_outlines[0][i + 1], self._mutable_outlines[1][i])
                frame = self.corrected_edge_plane(i, frame)
            _edge_planes[i] = Plane.from_frame(frame)
        return _edge_planes

    def set_extension_plane(self, edge_index, plane):
        self._extension_planes[edge_index] = self.corrected_edge_plane(edge_index, plane)

    def corrected_edge_plane(self, edge_index, plane):
        if dot_vectors(plane.normal, get_polyline_segment_perpendicular_vector(self._mutable_outlines[0], edge_index)) < 0:
            return Plane(plane.point, -plane.normal)
        return plane

    def apply_edge_extensions(self):
        for edge_index, plane in self._extension_planes.items():
            for polyline in self._mutable_outlines:
                move_polyline_segment_to_plane(polyline, edge_index, plane)

    @property
    def local_edge_planes(self):
        """Frames representing the edge planes of the plate in local coordinates.

        Returns
        -------
        list[:class:`~compas.geometry.Frame`]
            A list of frames representing the edge planes of the plate in local coordinates.
        """
        return [ep.transformed(self.transformation.inverse()) for ep in self.edge_planes]

    @reset_computed
    def reset(self):
        """Resets the element outlines to their initial state."""
        self._mutable_outlines = (self._original_outlines[0].copy(), self._original_outlines[1].copy())

    # ==========================================================================
    # Alternate constructors
    # ==========================================================================

    @classmethod
    def get_args_from_outlines(
        cls,
        outline_a,
        outline_b,
        openings=None,
    ):
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
        vector_to_XY = Vector.from_start_end(box.points[0], Point(0, 0, 0))
        local_outline_a = Polyline([pt.translated(vector_to_XY) for pt in rebased_pline_a.points])
        local_outline_b = Polyline([pt.translated(vector_to_XY) for pt in rebased_pline_b.points])
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

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        """
        Constructs a PlateGeometry from two polyline outlines. to be implemented to instantialte Plates and Slabs.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the plate geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the plate geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate geometry with the given outlines.
        """

        args = cls.get_from_outlines_args(outline_a, outline_b, openings)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        return cls(local_outline_a=args["local_outline_a"], local_outline_b=args["local_outline_b"], openings=args["openings"], **kwargs)

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
        openings : list[:class:`~compas_timber.elements.Opening`], optional
            A list of openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate geometry with the given outline and thickness.
        """
        # this ensure the plate geometry can always be computed
        if TOL.is_zero(thickness):
            thickness = TOL.absolute
        # TODO: @obucklin `vector` is never actually used here, at most it is used to determine the direction of the thickness vector which is always calculated from the outline.
        # TODO: is this the intention? should it maybe be replaced with some kind of a boolean flag?
        if TOL.is_zero(thickness):
            thickness = TOL.absolute
        offset_vector = Frame.from_points(outline[0], outline[1], outline[-2]).normal  # gets frame perpendicular to outline
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
            polyline_points = []
            for edge in loop.edges:
                polyline_points.append(edge.start_vertex.point)
            polyline_points.append(polyline_points[0])
            if loop.is_outer:
                outer_polyline = Polyline(polyline_points)
            else:
                inner_polylines.append(Polyline(polyline_points))
        return cls.from_outline_thickness(outer_polyline, thickness, vector=vector, openings=inner_polylines, **kwargs)

    # ==========================================================================
    #  Implementation of abstract methods
    # ==========================================================================

    @property
    def shape(self):
        # type: () -> compas.geometry.Brep
        """The shape of the plate before other features area applied.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The shape of the element.

        """
        outline_a = correct_polyline_direction(self._mutable_outlines[0], self.frame.normal, clockwise=True)
        outline_b = correct_polyline_direction(self._mutable_outlines[1], self.frame.normal, clockwise=True)
        plate_geo = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (outline_a, outline_b)])
        plate_geo.cap_planar_holes()
        for opening in self.openings:
            if not TOL.is_allclose(opening[0], opening[-1]):
                raise ValueError("Opening polyline is not closed.", opening[0], opening[-1])
            polyline_a = correct_polyline_direction(opening, self.frame.normal, clockwise=True)
            polyline_b = [closest_point_on_plane(pt, self.planes[1]) for pt in polyline_a.points]
            brep = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (polyline_a, polyline_b)])
            brep.cap_planar_holes()
            plate_geo -= brep
        return plate_geo

    def compute_elementgeometry(self):
        return self.shape

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
        obb.transform(Transformation.from_frame(self.frame))
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
    def _get_frame_and_dims_from_outlines(outline_a, outline_b):
        """Get the frame and dimensions from two outlines.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            The principal outline of the plate.
        outline_b : :class:`~compas.geometry.Polyline`
            The associated outline of the plate.

        Returns
        -------
        tuple[:class:`~compas.geometry.Frame`, float, float, float]
            A tuple containing the frame, length, width, and thickness.
        """
        frame = Frame.from_points(outline_a[0], outline_a[1], outline_a[-2])
        if dot_vectors(Vector.from_start_end(outline_a[0], outline_b[0]), frame.normal) < 0:
            frame = Frame.from_points(outline_a[0], outline_a[-2], outline_a[1])
        transform_to_world_xy = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        rebased_pts = [pt.transformed(transform_to_world_xy) for pt in outline_a.points + outline_b.points]
        box = Box.from_points(rebased_pts)
        frame = Frame(box.points[0], Vector(1, 0, 0), Vector(0, 1, 0))
        return frame.transformed(transform_to_world_xy.inverse()), box.xsize, box.ysize, box.zsize

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
