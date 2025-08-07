import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import bounding_box
from compas.geometry import cross_vectors
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import intersection_line_plane_param

from .timber import TimberElement


class Beam(TimberElement):
    """
    A class to represent timber beams (studs, slats, etc.) with rectangular cross-sections.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`
        A local coordinate system of the beam:
        Origin is located at the starting point of the centerline.
        x-axis corresponds to the centerline (major axis), usually also the fibre direction in solid wood beams.
        y-axis corresponds to the width of the cross-section, usually the smaller dimension.
        z-axis corresponds to the height of the cross-section, usually the larger dimension.
    length : float
        Length of the beam
    width : float
        Width of the cross-section
    height : float
        Height of the cross-section

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this beam.
    length : float
        Length of the beam.
    width : float
        Width of the cross-section
    height : float
        Height of the cross-section
    shape : :class:`~compas.geometry.Box`
        A feature-less box representing the parametric geometry of this beam.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this beam.
    ref_frame : :class:`~compas.geometry.Frame`
        Reference frame for machining processings according to BTLx standard.
    ref_sides : tuple(:class:`~compas.geometry.Frame`)
        A tuple containing the 6 frames representing the sides of the beam according to BTLx standard.
    ref_edges : tuple(:class:`~compas.geometry.Line`)
        A tuple containing the 4 lines representing the long edges of the beam according to BTLx standard.
    centerline : :class:`~compas.geometry.Line`
        A line representing the centerline of this beam.
    centerline_start : :class:`~compas.geometry.Point`
        The point at the start of the centerline of this beam.
    centerline_end : :class:`~compas.geometry.Point`
        The point at the end of the centerline of this beam.
    aabb : tuple(float, float, float, float, float, float)
        An axis-aligned bounding box of this beam as a 6 valued tuple of (xmin, ymin, zmin, xmax, ymax, zmax).
    long_edges : list(:class:`~compas.geometry.Line`)
        A list containing the 4 lines along the long axis of this beam.
    midpoint : :class:`~compas.geometry.Point`
        The point at the middle of the centerline of this beam.
    key : int, optional
        Once beam is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = super(Beam, self).__data__
        data["frame"] = self.frame
        data["width"] = self.width
        data["height"] = self.height
        data["length"] = self.length
        return data

    def __init__(self, frame, length, width, height, **kwargs):
        super(Beam, self).__init__(**kwargs)
        self.frame = frame
        self.width = width
        self.height = height
        self.length = length
        self.attributes = {}
        self.attributes.update(kwargs)
        self._blank_extensions = {}
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Beam(frame={!r}, length={}, width={}, height={})".format(self.frame, self.length, self.width, self.height)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_beam(self):
        return True

    @property
    def shape(self):
        # type: () -> Box
        assert self.frame
        return self._create_shape()

    @property
    def blank(self):
        # type: () -> Box
        return self._create_blank()

    @property
    def blank_length(self):
        # type: () -> float
        start, end = self._resolve_blank_extensions()
        return self.length + start + end

    @property
    def centerline(self):
        # type: () -> Line
        return Line(self.centerline_start, self.centerline_end)

    @property
    def centerline_start(self):
        # type: () -> Point
        assert self.frame
        return self.frame.point

    @property
    def centerline_end(self):
        # type: () -> Point
        assert self.frame
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length))

    @property
    def long_edges(self):
        # TODO: can we replace this with `ref_edges`? No because ref_edges get affected by blank extensions
        # type: () -> list[Line]
        assert self.frame
        y = self.frame.yaxis
        z = self.frame.zaxis
        w = self.width * 0.5
        h = self.height * 0.5
        ps = self.centerline_start
        pe = self.centerline_end

        return [Line(ps + v, pe + v) for v in (y * w + z * h, -y * w + z * h, -y * w - z * h, y * w - z * h)]

    @property
    def midpoint(self):
        assert self.frame
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length * 0.5))

    def __str__(self):
        return "Beam {:.3f} x {:.3f} x {:.3f} at {}".format(
            self.width,
            self.height,
            self.length,
            self.frame,
        )

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_elementgeometry(self, include_features=True):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the element in local coordinates.

        This is the parametric representation of the element,
        without considering its location in the model or its interaction(s) with connected elements.

        Parameters
        ----------
        include_features : bool, optional
            If True, the features should be included in the element geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`

        """
        blank_geo = Brep.from_box(self.blank)  # blank is in global coordinates
        if include_features:
            for feature in self.features:
                try:
                    blank_geo = feature.apply(blank_geo, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        blank_geo.transform(self.transformation.inverse())  # transform back to local coordinates
        return blank_geo

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
        vertices, _ = self.blank.to_vertices_and_faces()
        box = Box.from_bounding_box(bounding_box(vertices))
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Parameters
        ----------
        inflate : float
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        obb = self.blank.copy()
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        return obb

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.blank.to_mesh()

    # ==========================================================================
    # Alternative constructors
    # ==========================================================================

    @classmethod
    def from_centerline(cls, centerline, width, height, z_vector=None):
        """Define the beam from its centerline.

        Parameters
        ----------
        centerline : :class:`~compas.geometry.Line`
            The centerline of the beam to be created.
        length : float
            Length of the beam.
        width : float
            Width of the cross-section.
        height : float
            Height of the cross-section.
        z_vector : :class:`~compas.geometry.Vector`
            A vector indicating the height direction (z-axis) of the cross-section.
            Defaults to WorldZ or WorldX depending on the centerline's orientation.

        Returns
        -------
        :class:`~compas_timber.parts.Beam`

        """
        if centerline.length < TOL.absolute:
            raise ValueError("The given centerline has zero length. Check your endpoints.")
        x_vector = centerline.vector
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        if y_vector.length < TOL.absolute:
            raise ValueError("The given z_vector seems to be parallel to the given centerline.")
        frame = Frame(centerline.start, x_vector, y_vector)
        length = centerline.length

        return cls(frame, length, width, height)

    @classmethod
    def from_endpoints(cls, point_start, point_end, width, height, z_vector=None):
        """Creates a Beam from the given endpoints.

        Parameters
        ----------
        point_start : :class:`~compas.geometry.Point`
            The start point of a centerline
        end_point : :class:`~compas.geometry.Point`
            The end point of a centerline
        width : float
            Width of the cross-section.
        height : float
            Height of the cross-section.
        z_vector : :class:`~compas.geometry.Vector`
            A vector indicating the height direction (z-axis) of the cross-section.
            Defaults to WorldZ or WorldX depending on the centerline's orientation.

        Returns
        -------
        :class:`~compas_timber.parts.Beam`

        """
        line = Line(point_start, point_end)
        return cls.from_centerline(line, width, height, z_vector)

    def _create_shape(self):
        # type: () -> Box
        boxframe = self.frame
        depth_offset = boxframe.xaxis * self.length * 0.5
        boxframe.point += depth_offset
        return Box(self.length, self.width, self.height, frame=boxframe)

    def _create_blank(self):
        # type: () -> Box
        origin = self.ref_frame.point.copy()
        origin += (self.ref_frame.xaxis * self.blank_length + self.ref_frame.yaxis * self.height + self.ref_frame.zaxis * self.width) / 2  # center the origin
        frame = Frame(origin, self.ref_frame.xaxis, self.ref_frame.zaxis)
        return Box(self.blank_length, self.width, self.height, frame=frame)

    # ==========================================================================
    # Featrues
    # ==========================================================================

    def add_blank_extension(self, start, end, joint_key=None):
        # type: (float, float, None | int) -> None
        """Adds a blank extension to the beam.

        start : float
            The amount by which the start of the beam should be extended.
        end : float
            The amount by which the end of the beam should be extended.
        joint_key : int
            The key of the joint which required this extension. When the joint is removed,
            this extension will be removed as well.

        """
        if joint_key is not None and joint_key in self._blank_extensions:
            s, e = self._blank_extensions[joint_key]
            start += s
            end += e
        self._blank_extensions[joint_key] = (start, end)

    def remove_blank_extension(self, joint_key=None):
        # type: (None | int) -> None
        """Removes a blank extension from the beam.

        Parameters
        ----------
        joint_key : int
            The key of the joint which required this extension.

        """
        if joint_key is None:
            self._blank_extensions = {}
        else:
            del self._blank_extensions[joint_key]

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

    def _resolve_blank_extensions(self):
        # type: () -> tuple[float, float]
        """Returns the max amount by which to extend the beam at both ends."""
        start = 0.0
        end = 0.0
        for s, e in self._blank_extensions.values():
            start = max(start, s)
            end = max(end, e)
        return start, end

    def extension_to_plane(self, plane):
        # type: (Frame) -> tuple[float, float]
        """Returns the amount by which to extend the beam in each direction using metric units.

        The extension is the minimum amount which allows all long faces of the beam to pass through
        the given plane.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Frame` or :class:`~compas.geometry.Plane`
            The plane to which the beam should be extended.

        Returns
        -------
        tuple(float, float)
            Extension amount at start of beam, Extension amount at end of beam

        """
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        x = {}
        for e in self.long_edges:
            p, t = intersection_line_plane_param(e, plane)
            x[t] = p

        px = intersection_line_plane_param(self.centerline, plane)[0]
        if px is None:
            raise ValueError("The plane does not intersect with the centerline of the beam.")
        side, _ = self.endpoint_closest_to_point(px)

        ds = 0.0
        de = 0.0
        if side == "start":
            tmin = min(x.keys())
            ds = tmin * self.length  # should be negative
        elif side == "end":
            tmax = max(x.keys())
            de = (tmax - 1.0) * self.length
        return -ds, de

    @staticmethod
    def _calculate_z_vector_from_centerline(centerline_vector):
        # type: (Vector) -> Vector
        z = Vector(0, 0, 1)
        angle = angle_vectors(z, centerline_vector)
        if angle < TOL.angular or angle > math.pi - TOL.angular:
            z = Vector(1, 0, 0)
        return z

    def endpoint_closest_to_point(self, point):
        # type: (Point) -> tuple[str, Point]
        """Returns which endpoint of the centerline of the beam is closer to the given point.

        Parameters
        ----------
        point : :class:`~compas.geometry.Point`
            The point of interest.

        Returns
        -------
        list(str, :class:`~compas.geometry.Point`)
            Two element list. First element is either 'start' or 'end' depending on the result.
            The second element is the actual endpoint of the beam's centerline which correspond to the result.

        """
        ps = self.centerline_start
        pe = self.centerline_end
        ds = point.distance_to_point(ps)
        de = point.distance_to_point(pe)

        if ds <= de:
            return "start", ps
        else:
            return "end", pe
