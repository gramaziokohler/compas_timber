from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import PlanarSurface
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import closest_point_on_plane
from compas.geometry import distance_point_plane
from compas.geometry import dot_vectors
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour
from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_polyline_clockwise

from .timber import TimberElement


class Plate(TimberElement):
    """
    A class to represent timber plates (plywood, CLT, etc.) defined by polylines on top and bottom faces of material.

    Parameters
    ----------
    outline_a : :class:`~compas.geometry.Polyline`                                                  TODO: add support for NurbsCurve
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.
    blank_extension : float, optional
        The extension of the blank geometry around the edges of the plate geometry. Default is 0.


    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate.
    blank_length : float
        Length of the plate blank.
    width : float
        Thickness of the plate material.
    height : float
        Height of the plate blank.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this plate.
    ref_frame : :class:`~compas.geometry.Frame`
        Reference frame for machining processings according to BTLx standard.
    ref_sides : tuple(:class:`~compas.geometry.Frame`)
        A tuple containing the 6 frames representing the sides of the plate according to BTLx standard.
    aabb : tuple(float, float, float, float, float, float)
        An axis-aligned bounding box of this plate as a 6 valued tuple of (xmin, ymin, zmin, xmax, ymax, zmax).
    key : int, optional
        Once plate is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = super(Plate, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["blank_extension"] = self.blank_extension
        data["openings"] = self.openings
        return data

    def __init__(self, outline_a=None, outline_b=None, openings=None, **kwargs):
        super(Plate, self).__init__(**kwargs)
        Plate.check_outlines(outline_a, outline_b)
        self._input_outlines = (Polyline(outline_a.points), Polyline(outline_b.points))
        self.outline_a = Polyline(outline_a.points)
        self.outline_b = Polyline(outline_b.points)
        self._outline_feature = None
        self._opening_features = None
        self._frame = None
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self._ref_frame = None
        self._blank = None
        self._planes = None
        self._thickness = None
        self.interfaces = []
        self.openings = []
        if openings:
            for opening in openings:
                self.openings.append(Polyline([closest_point_on_plane(pt, self.planes[0]) for pt in opening]))

    def __repr__(self):
        # type: () -> str
        return "Plate(outline_a={!r}, outline_b={!r})".format(self.outline_a, self.outline_b)

    def __str__(self):
        return "Plate {}, {} ".format(self.outline_a, self.outline_b)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_plate(self):
        return True

    @property
    def outlines(self):
        return (self.outline_a, self.outline_b)

    @property
    def blank(self):
        if not self._blank:
            self._blank = self.obb.copy()
            self._blank.xsize += 2 * self.attributes.get("blank_extension", 0.0)
            self._blank.ysize += 2 * self.attributes.get("blank_extension", 0.0)
        return self._blank

    @property
    def thickness(self):
        if self._thickness is None:
            self._thickness = distance_point_plane(self.outline_b[0], Plane.from_frame(self.frame))
        return self._thickness

    @property
    def planes(self):
        if not self._planes:
            self._planes = (Plane.from_frame(self.frame), Plane.from_frame(self.frame.translated(self.thickness * self.frame.normal)))
        return self._planes

    @property
    def blank_length(self):
        return self.blank.xsize

    @property
    def width(self):
        return self.blank.zsize

    @property
    def height(self):
        return self.blank.ysize

    @property
    def ref_frame(self):
        if not self._ref_frame:
            self._ref_frame = Frame(self.blank.points[0], self.frame.xaxis, self.frame.yaxis)
        return self._ref_frame

    @property
    def ref_sides(self):
        # type: () -> tuple[Frame, Frame, Frame, Frame, Frame, Frame]
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        # TODO: cache these
        rs1_point = self.ref_frame.point
        rs2_point = rs1_point + self.ref_frame.yaxis * self.height
        rs3_point = rs1_point + self.ref_frame.yaxis * self.height + self.ref_frame.zaxis * self.width
        rs4_point = rs1_point + self.ref_frame.zaxis * self.width
        rs5_point = rs1_point
        rs6_point = rs1_point + self.ref_frame.xaxis * self.blank_length + self.ref_frame.yaxis * self.height
        return (
            Frame(rs1_point, self.ref_frame.xaxis, self.ref_frame.zaxis, name="RS_1"),
            Frame(rs2_point, self.ref_frame.xaxis, -self.ref_frame.yaxis, name="RS_2"),
            Frame(rs3_point, self.ref_frame.xaxis, -self.ref_frame.zaxis, name="RS_3"),
            Frame(rs4_point, self.ref_frame.xaxis, self.ref_frame.yaxis, name="RS_4"),
            Frame(rs5_point, self.ref_frame.zaxis, self.ref_frame.yaxis, name="RS_5"),
            Frame(rs6_point, self.ref_frame.zaxis, -self.ref_frame.yaxis, name="RS_6"),
        )

    @property
    def features(self):
        if not self._outline_feature:
            self._outline_feature = FreeContour.from_top_bottom_and_elements(self.outline_a, self.outline_b, self, interior=False)
        if not self._opening_features:
            self._opening_features = [FreeContour.from_polyline_and_element(o, self, interior=True) for o in self.openings]
        return [self._outline_feature] + self._opening_features + self._features

    @features.setter
    def features(self, features):
        # type: (list[FreeContour]) -> None
        """Sets the features of the plate."""
        self._features = features

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    @property
    def frame(self):
        if not self._frame:
            self._frame = Frame.from_points(self.outline_a[0], self.outline_a[1], self.outline_a[-2])
            if dot_vectors(Vector.from_start_end(self.outline_a[0], self.outline_b[0]), self._frame.normal) < 0:
                self._frame = Frame.from_points(self.outline_a[0], self.outline_a[-2], self.outline_a[1])
        return self._frame

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self._features = []
        self._outline_feature = None
        self._opening_features = None
        self.outline_a = Polyline(self._input_outlines[0].points)
        self.outline_b = Polyline(self._input_outlines[1].points)
        self.debug_info = []

    def add_interface(self, interface):
        self.interfaces.append(interface)

    def check_outlines(outline_a, outline_b):
        # type: (compas.geometry.Polyline, compas.geometry.Polyline) -> bool
        """Checks if the outlines are valid.

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

    def side_as_surface(self, side_index):
        # type: (int) -> compas.geometry.PlanarSurface
        """Returns the requested side of the beam as a parametric planar surface.

        Parameters
        ----------
        side_index : int
            The index of the reference side to be returned. 0 to 5.

        """
        # TODO: maybe this should be the default representation of the ref sides?
        ref_side = self.ref_sides[side_index]
        if side_index in (0, 2):  # top + bottom
            xsize = self.blank_length
            ysize = self.width
        elif side_index in (1, 3):  # sides
            xsize = self.blank_length
            ysize = self.height
        elif side_index in (4, 5):  # ends
            xsize = self.width
            ysize = self.height
        return PlanarSurface(xsize, ysize, frame=ref_side, name=ref_side.name)

    # ==========================================================================
    # Alternate constructors
    # ==========================================================================

    @classmethod
    def from_outline_thickness(cls, outline, thickness, vector=None, openings=None, **kwargs):
        """
        Constructs a plate from a polyline outline and a thickness.
        The outline is the top face of the plate, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the plate.
        thickness : float
            The thickness of the plate.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        blank_extension : float, optional
            The extension of the blank geometry around the edges of the plate geometry. Default is 0.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate with the given outline and thickness.
        """
        # this ensure the plate's geometry can always be computed
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
        return cls(outline, outline_b, openings=openings, **kwargs)

    @classmethod
    def from_brep(cls, brep, thickness, vector=None, **kwargs):
        """Creates a plate from a brep.

        Parameters
        ----------
        brep : :class:`compas.geometry.Brep`
            The brep of the plate.
        thickness : float
            The thickness of the plate.
        vector : :class:`compas.geometry.Vector`
            The vector in which the plate is extruded.(optional)
        kwargs : dict
            Additional keyword arguments.
            These are passed to the :class:`compas_timber.elements.Slab` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate with the given brep and thickness.
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
    #  methods
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
        outline_a = correct_polyline_direction(self.outline_a, self.frame.normal, clockwise=True)
        outline_b = correct_polyline_direction(self.outline_b, self.frame.normal, clockwise=True)
        plate_geo = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (outline_a, outline_b)])
        plate_geo.cap_planar_holes()
        for pline in self.openings:
            if not TOL.is_allclose(pline[0], pline[-1]):
                raise ValueError("Opening polyline is not closed.", pline[0], pline[-1])
            polyline = correct_polyline_direction(pline, self.frame.normal, clockwise=True)
            polyline_b = [closest_point_on_plane(pt, self.planes[1]) for pt in polyline]
            brep = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (polyline, polyline_b)])
            brep.cap_planar_holes()
            plate_geo -= brep
        return plate_geo

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the plate shape.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        plate_geo = self.shape
        if include_features:
            for feature in self._features:
                try:
                    plate_geo = feature.apply(plate_geo, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
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
        vertices = self.outline_a.points + self.outline_b.points
        world_vertices = []
        for point in vertices:
            world_vertices.append(point.transformed(Transformation.from_frame_to_frame(self.frame, Frame.worldXY())))
        obb = Box.from_points(world_vertices)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        obb.transform(Transformation.from_frame_to_frame(Frame.worldXY(), self.frame))
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

    def opp_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the the side that is directly across from the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the opposite side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the opposite side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index + 2) % 4]
