import math

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas_future.datastructures import GeometricFeature
from compas_future.datastructures import ParametricFeature
from compas_future.datastructures import Part

from compas_timber.utils.compas_extra import intersection_line_plane
from compas_timber.utils.helpers import close  # TODO: remove this

# TODO: update to global compas PRECISION
ANGLE_TOLERANCE = 1e-3  # [radians]
DEFAULT_TOLERANCE = 1e-6


def _create_box(frame, xsize, ysize, zsize):
    # mesh reference point is always worldXY, geometry is transformed to actual frame on Beam.geometry
    # TODO: Alternative: Add frame information to MeshGeometry, otherwise Frame is only implied by the vertex values
    boxframe = frame.copy()
    depth_offset = boxframe.xaxis * xsize * 0.5
    boxframe.point += depth_offset
    return Box(boxframe, xsize, ysize, zsize)


def _create_mesh_shape(xsize, ysize, zsize):
    box = _create_box(Frame.worldXY(), xsize, ysize, zsize)
    return Mesh.from_vertices_and_faces(*box.to_vertices_and_faces(True))


def _create_brep_shape(xsize, ysize, zsize):
    box = _create_box(Frame.worldXY(), xsize, ysize, zsize)
    return Brep.from_box(box)


class Beam(Part):
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
    geometry_type : str
        The type of geometry created for this beam. Either 'mesh' or 'brep.

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
    geometry_type : str
        The type of geometry created by this beam. Either 'mesh' or 'brep'.
    tolerance : float
    shape : :class:`~compas.geometry.Box`
        A feature-less box representing the parametric geometry of this beam.
        The default tolerance used in operations performed on this beam.
    faces : list(:class:`~compas.geometry.Frame`)
        A list of frames representing the 6 faces of this beam.
        0: +y (side's frame normal is equal to the beam's Y positive direction)
        1: +z
        2: -y
        3: -z
        4: -x (side at the starting end)
        5: +x (side at the end of the beam)
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

    """

    SHAPE_FACTORIES = {
        "mesh": _create_mesh_shape,
        "brep": _create_brep_shape,
    }

    def __init__(self, frame, length, width, height, geometry_type, **kwargs):
        super(Beam, self).__init__(frame=frame)
        # TODO: add setter so that only that makes sure the frame is orthonormal --> needed for comparisons
        self.frame = frame
        self.width = width
        self.height = height
        self.length = length
        self.geometry_type = geometry_type
        self._geometry = self._create_beam_shape_from_params(self.length, self.width, self.height, self.geometry_type)
        self._geometry_with_features = self._geometry.copy()

    @property
    def data(self):
        """
        Workaround: overrides Part.data since serialization of Beam using Data.from_data is not supported.
        """
        data = {"width": self.width, "height": self.height, "length": self.length, "geometry_type": self.geometry_type}
        data.update(super(Beam, self).data)
        return data

    @data.setter
    def data(self, data):
        """
        Workaround: overrides Part.data.setter since de-serialization of Beam using Data.from_data is not supported.
        """
        Part.data.fset(self, data)
        self.width = data["width"]
        self.height = data["height"]
        self.length = data["length"]
        self.geometry_type = data["geometry_type"]

    @property
    def tolerance(self):
        return DEFAULT_TOLERANCE

    @property
    def shape(self):
        return _create_box(self.frame, self.length, self.width, self.height)

    @property
    def faces(self):
        return [
            Frame(
                Point(*add_vectors(self.midpoint, self.frame.yaxis * self.width * 0.5)),
                self.frame.xaxis,
                -self.frame.zaxis,
            ),
            Frame(
                Point(*add_vectors(self.midpoint, -self.frame.zaxis * self.height * 0.5)),
                self.frame.xaxis,
                -self.frame.yaxis,
            ),
            Frame(
                Point(*add_vectors(self.midpoint, -self.frame.yaxis * self.width * 0.5)),
                self.frame.xaxis,
                self.frame.zaxis,
            ),
            Frame(
                Point(*add_vectors(self.midpoint, self.frame.zaxis * self.height * 0.5)),
                self.frame.xaxis,
                self.frame.yaxis,
            ),
            Frame(self.frame.point, -self.frame.yaxis, self.frame.zaxis),  # small face at start point
            Frame(
                Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length)),
                self.frame.yaxis,
                self.frame.zaxis,
            ),  # small face at end point
        ]

    @property
    def centerline(self):
        return Line(self.centerline_start, self.centerline_end)

    @property
    def centerline_start(self):
        return self.frame.point

    @property
    def centerline_end(self):
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length))

    @property
    def aabb(self):
        vertices = self.shape.vertices
        x = [p.x for p in vertices]
        y = [p.y for p in vertices]
        z = [p.z for p in vertices]
        return tuple(min(x), min(y), min(z), max(x), max(y), max(z))

    @property
    def long_edges(self):
        y = self.frame.yaxis
        z = self.frame.zaxis
        w = self.width * 0.5
        h = self.height * 0.5
        ps = self.centerline_start
        pe = self.centerline_end

        return [Line(ps + v, pe + v) for v in (y * w + z * h, -y * w + z * h, -y * w - z * h, y * w - z * h)]

    @property
    def midpoint(self):
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length * 0.5))

    @property
    def has_features(self):
        # TODO: move to compas_future... Part
        return len(self.features) > 0

    @staticmethod
    def _create_beam_shape_from_params(width, height, length, geometry_type):
        try:
            factory = Beam.SHAPE_FACTORIES[geometry_type]
            return factory(width, height, length)
        except KeyError:
            raise ValueError("Expected one of {} got instaed: {}".format(Beam.SHAPE_FACTORIES.keys(), geometry_type))

    def __str__(self):
        return "Beam {:.3f} x {:.3f} x {:.3f} at {}".format(
            self.width,
            self.height,
            self.length,
            self.frame,
        )

    def update_beam_geometry(self):
        """Resets the geometry representation of the beam accroding to the current parametric values.

        Should be called after each update to the paramteric definition of the beam.

        """
        self._geometry_with_features = self._create_beam_shape_from_params(
            self.length, self.width, self.height, self.geometry_type
        )

    def is_identical(self, other):
        """Returns True if the other beam's values are identicale, within TOLERANCE, to the ones of this beam.

        Returns
        -------
        bool

        """
        return (
            isinstance(other, Beam)
            and close(self.width, other.width, DEFAULT_TOLERANCE)
            and close(self.height, other.height, DEFAULT_TOLERANCE)
            and close(self.length, other.length, DEFAULT_TOLERANCE)
            and self.frame == other.frame
            # TODO: skip joints and features ?
        )

    @classmethod
    def from_data(cls, data):
        """Alternative to None default __init__ parameters.

        """
        obj = cls(**data)
        obj.data = data
        return obj

    def get_geometry(self, with_features=False):
        """Returns the geometry representation of this beam.

        The geometry is transformed to the frame of this beam.

        Parameters
        ----------
        with_features : bool
            If True the geometry returned should include the features, if any.

        Returns
        -------
        :class:`compas.geometry.Geometry`


        """
        transformation = Transformation.from_frame(self.frame)
        if not with_features or not self.features:
            g_copy = self._geometry.copy()
        else:
            g_copy = self._geometry_with_features.copy()
        g_copy.transform(transformation)
        return g_copy

    def add_feature(self, feature, apply=False):
        """Adds a feature to this beam.

        If apply is False, `apply_features` must be called for the features to be represented in the geometry.

        feature : :class:`~compas.datastructures.Feature`
            The feature to be added to this beam.
        apply : bool
            If True, the feature will be applied to the beam's geometry upon adding it.

        """
        self.features.append(feature)
        if apply:
            self.apply_features()

    def apply_features(self):
        """Applies the features which were added to this beam.

        This method separatelly applies the parametric and geometric features.
        The parametric features, if any, are accumulated when possible.

        Returns
        -------
        list(str)
            A list of errors which occurred during the application of the features, if any, to assist with debugging.

        """
        error_log = []
        para_features = [f for f in self.features if isinstance(f, ParametricFeature)]
        geo_features = [f for f in self.features if isinstance(f, GeometricFeature)]
        for f in para_features:
            success, _ = f.apply(self)
            if not success:
                error_log.append(self._create_feature_error_msg(f, self))
        for f in geo_features:
            success, self._geometry_with_features = f.apply(self)
            self._geometry_with_features.transform(Transformation.from_frame_to_frame(self.frame, Frame.worldXY()))
            if not success:
                error_log.append(self._create_feature_error_msg(f, self))
        return error_log

    @staticmethod
    def _create_feature_error_msg(feature, part):
        msg = "Failed applying feature: {!r} with owner: {!r} to beam: {!r}"
        return msg.format(feature, getattr(feature, "_owner", None), part)

    def clear_features(self, features_to_clear=None):
        """Clears applied features and restores their effect.

        Selective removal of features is possible by providing a list of features which shall be removed.
        In such case, all features are restored and the remaining features are reapplied.

        Parameters
        ----------
        features_to_clear : list(:class:`compas.datastructures.Feature`)
            If provided, only the features which are in this list shall be removed.

        """
        if features_to_clear:
            self.features = [f for f in self.features if f not in features_to_clear]
        else:
            self.features = []
        self._geometry_with_features = self._geometry.copy()

    @classmethod
    def from_centerline(cls, centerline, width, height, z_vector=None, geometry_type="brep"):
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
        gemetry_type : str
            The type of geometry to use when creating this beam. Either 'mesh' of 'brep'.

        Returns
        -------
        :class:`~compas_timber.parts.Beam`

        """
        x_vector = centerline.vector
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        if y_vector.length < DEFAULT_TOLERANCE:
            raise ValueError("The given z_vector seems to be parallel to the given centerline.")
        frame = Frame(centerline.start, x_vector, y_vector)
        length = centerline.length

        return cls(frame, length, width, height, geometry_type)

    @classmethod
    def from_endpoints(cls, point_start, point_end, width, height, z_vector=None, geometry_type="brep"):
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
        gemetry_type : str
            The type of geometry to use when creating this beam. Either 'mesh' of 'brep'.

        Returns
        -------
        :class:`~compas_timber.parts.Beam`

        """
        line = Line(point_start, point_end)
        return cls.from_centerline(line, width, height, z_vector, geometry_type)

    def move_endpoint(self, vector=Vector(0, 0, 0), which_endpoint="start"):
        """Deprecated?

        """
        z = self.frame.zaxis
        ps = self.centerline_start
        pe = self.centerline_end
        if which_endpoint in ("start", "both"):
            ps = add_vectors(ps, vector)
        if which_endpoint in ("end", "both"):
            pe = add_vectors(pe, vector)
        x = Vector.from_start_end(ps, pe)
        y = Vector(*cross_vectors(x, z)) * -1.0
        frame = Frame(ps, x, y)
        self.frame = frame
        self.length = distance_point_point(ps, pe)

    def extension_to_plane(self, pln):
        """Returns the amount by which to extend the beam in each direction using metric units.

        TODO: verify this is true
        The extension is the minimum amount which allows all long faces of the beam to pass through
        the given plane.

        Returns
        -------
        tuple(float, float)
            Extension amount at start of beam, Extension amount at end of beam

        """
        x = {}
        pln = Plane.from_frame(pln)
        for e in self.long_edges:
            p, t = intersection_line_plane(e, pln)
            x[t] = p

        px = intersection_line_plane(self.centerline, pln)[0]
        side, _ = self.endpoint_closest_to_point(px)

        ds = 0.0
        de = 0.0
        if side == "start":
            tmin = min(x.keys())
            if tmin < 0.0:
                ds = tmin * self.length  # should be negative
        elif side == "end":
            tmax = max(x.keys())
            if tmax > 1.0:
                de = (tmax - 1.0) * self.length

        return -ds, de

    def extend_ends(self, d_start, d_end):
        """Extends the beam's parametric definition at both ends by the given values.

        Extensions at the start of the centerline should have a negative value.
        Extenshions at the end of the centerline should have a positive value.
        Otherwise the centerline will be shortend, not extended.

        The geometry of the beam is subsequently updated to match the new values.

        Parameters
        ----------
        d_start : float
            The amount by which the start of the beam's centerline should be extended, in design units.
        d_end : float
            The amount by which the end of the beam's centerline should be extended, in design units.

        """
        self.frame.point += -self.frame.xaxis * d_start  # "extension" to the start edge
        extension = d_start + d_end
        self.length += extension
        self.update_beam_geometry()

    def align_z(self, vector):
        """Align the z_axis of the beam's definition with the given vector.

        TODO: Not used anywhere. Needed?

        Parameters
        ----------
        vector : :class:`~compas.geometry.Vector`
            The vector with which to align the z_axis.

        """
        y_vector = Vector(*cross_vectors(self.frame.xaxis, vector)) * -1.0
        frame = Frame(self.frame.point, self.frame.xaxis, y_vector)
        self.frame = frame

    @staticmethod
    def _calculate_z_vector_from_centerline(centerline_vector):
        z = Vector(0, 0, 1)
        angle = angle_vectors(z, centerline_vector)
        if angle < ANGLE_TOLERANCE or angle > math.pi - ANGLE_TOLERANCE:
            z = Vector(1, 0, 0)
        return z

    def endpoint_closest_to_point(self, point):
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
            return ["start", ps]
        else:
            return ["end", pe]
