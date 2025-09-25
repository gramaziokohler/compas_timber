from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import closest_point_on_plane
from compas.geometry import dot_vectors
from compas.geometry import bounding_box_xy
from compas.tolerance import TOL
from compas_model.elements import reset_computed


from compas_timber.utils import correct_polyline_direction
from compas_timber.utils import is_polyline_clockwise



class Sheet(object):
    """
    A class to represent plate-like objects (plate, slab, etc.) defined by polylines on top and bottom faces of shape.

    Parameters
    ----------
    outline_a : :class:`~compas.geometry.Polyline`                                                  TODO: add support for NurbsCurve
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.
    openings : list(:class:`~compas_timber.elements.Opening`), optional
        A list of Opening objects representing openings in this plate.
    **kwargs : dict, optional
        Additional keyword arguments to be passed to the constructor of :class:`~compas_timber.elements.TimberElement`.

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
        data = super(Sheet, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["openings"] = self.openings
        return data

    def __init__(self, outline_a=None, outline_b=None, openings=None, frame=None):
        Sheet.check_outlines(outline_a, outline_b)
        self._input_outlines = (Polyline(outline_a.points), Polyline(outline_b.points))
        self.frame = frame or self.get_frame(outline_a, outline_b) or Frame.worldXY()
        self.local_outlines = ((outline_a.transformed(self.transformation.inverse())), (outline_b.transformed(self.transformation.inverse())))
        self.outline_a = Polyline(outline_a.points)
        self.outline_b = Polyline(outline_b.points)
        self._frame = None
        self._planes = None
        self._edge_planes = []

        self.openings = openings or []

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
    def thickness(self):
        return self.obb.width

    @property
    def planes(self):
        if not self._planes:
            self._planes = (Plane.from_frame(self.frame), Plane.from_frame(self.frame.translated(self.thickness * self.frame.normal)))
        return self._planes

    @property
    def length(self):
        return self.obb.xsize

    @property
    def width(self):
        return self.obb.zsize

    @property
    def height(self):
        return self.obb.ysize

    @property
    def normal(self):
        """Normal vector of the plate."""
        return self.frame.normal


    def get_frame(self, outline_a, outline_b):
        """The slab_populator frame in global space."""
        frame = Frame.from_points(outline_a[0], outline_a[1], outline_a[-2])
        if dot_vectors(Vector.from_start_end(outline_a[0], outline_b[0]), frame.normal) < 0:
            frame = Frame.from_points(outline_a[0], outline_a[-2], outline_a[1])
        transform_to_world_xy = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        rebased_pts = [pt.transformed(transform_to_world_xy) for pt in outline_a.points + outline_b.points]
        frame_offset = bounding_box_xy(rebased_pts)[0]
        translate_vector = frame.xaxis * frame_offset[0] + frame.yaxis * frame_offset[1]
        frame.translate(translate_vector)
        return frame

    @property
    def edge_planes(self):
        if not self._edge_planes:
            for i in range(len(self.local_outlines[0]) - 1):
                plane = Frame.from_points(self.local_outlines[0][i], self.local_outlines[0][i + 1], self.local_outlines[1][i])
                if dot_vectors(plane.normal, get_polyline_segment_perpendicular_vector(self.local_outlines[0], i)) < 0:
                    plane = Frame(plane.point, plane.xaxis, -plane.yaxis)
                self._edge_planes.append(plane)
        return self._edge_planes

    @reset_computed
    def reset(self):
        """Resets the element outlines to their initial state."""
        self.outline_a = Polyline(self._input_outlines[0].points)
        self.outline_b = Polyline(self._input_outlines[1].points)
        self._edge_planes = []

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

    # ==========================================================================
    # Alternate constructors
    # ==========================================================================

    @classmethod
    def from_outline_thickness(cls, outline, thickness, vector=None, openings=None, **kwargs):
        """
        Constructs a sheet from a polyline outline and a thickness.
        The outline is the top face of the sheet, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the sheet.
        thickness : float
            The thickness of the sheet.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        openings : list(:class:`compas_timber.elements.Opening`), optional
            A list of openings to be added to the sheet.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Sheet`
            A Sheet object representing the sheet with the given outline and thickness.
        """
        # this ensure the sheet's geometry can always be computed
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
    #  Implementation of abstract methods
    # ==========================================================================

    @property
    def transformation(self):
        return Transformation.from_frame(self.frame)

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
        for opening in self.openings:
            if not TOL.is_allclose(opening.outline_a[0], opening.outline_a[-1]):
                raise ValueError("Opening polyline is not closed.", opening.outline_a[0][0], opening.outline_a[0][-1])
            polyline_a = correct_polyline_direction(opening.outline_a, self.frame.normal, clockwise=True)
            if not opening.outline_b:
                polyline_b = [closest_point_on_plane(pt, self.planes[1]) for pt in opening.outline_a]
            else:
                polyline_b = correct_polyline_direction(opening.outline_b, self.frame.normal, clockwise=True)
            brep = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (polyline_a, polyline_b)])
            brep.cap_planar_holes()
            plate_geo -= brep
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

        obb = Box.from_points(self.local_outlines[0].points + self.local_outlines[1].points)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        obb.transform(self.transformation)
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
