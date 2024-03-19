import math

from compas.datastructures import Part
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors

from compas_timber.utils.compas_extra import intersection_line_plane

ANGLE_TOLERANCE = 1e-3  # [radians]
DEFAULT_TOLERANCE = 1e-6


def _create_box(frame, xsize, ysize, zsize):
    # mesh reference point is always worldXY, geometry is transformed to actual frame on Beam.geometry
    # TODO: Alternative: Add frame information to MeshGeometry, otherwise Frame is only implied by the vertex values
    boxframe = frame.copy()
    depth_offset = boxframe.xaxis * xsize * 0.5
    boxframe.point += depth_offset
    return Box(xsize, ysize, zsize, frame=boxframe)


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

    def __init__(self, frame, length, width, height, **kwargs):
        super(Beam, self).__init__(frame=frame)
        self.width = width
        self.height = height
        self.length = length
        self.features = []
        self._blank_extensions = {}

    @property
    def __data__(self):
        data = {
            "frame": self.frame.__data__,
            "key": self.key,
            "width": self.width,
            "height": self.height,
            "length": self.length,
        }
        return data

    @classmethod
    def __from_data__(cls, data):
        instance = cls(Frame.__from_data__(data["frame"]), data["length"], data["width"], data["height"])
        instance.key = data["key"]
        return instance

    @property
    def shape(self):
        return _create_box(self.frame, self.length, self.width, self.height)

    @property
    def blank(self):
        return _create_box(self.blank_frame, self.blank_length, self.width, self.height)

    @property
    def blank_length(self):
        start, end = self._resolve_blank_extensions()
        return self.length + start + end

    @property
    def blank_frame(self):
        start, _ = self._resolve_blank_extensions()
        frame = self.frame.copy()
        frame.point += -frame.xaxis * start  # "extension" to the start edge
        return frame

    @property
    def part_ref(self):
        frame = self.blank_frame
        return Frame(
            Point(*(frame.point + (frame.yaxis * self.width * 0.5) - (frame.zaxis * self.height * 0.5))),
            frame.xaxis,
            frame.zaxis,
        )

    @property
    def faces(self):
        frame = self.part_ref
        return [
            Frame(
                frame.point,
                self.frame.xaxis,
                -self.frame.yaxis,
            ),
            Frame(
                Point(*add_vectors(frame.point, self.frame.zaxis * self.height)),
                self.frame.xaxis,
                -self.frame.zaxis,
            ),
            Frame(
                Point(*(frame.point - self.frame.yaxis * self.width + self.frame.zaxis * self.height)),
                self.frame.xaxis,
                self.frame.yaxis,
            ),
            Frame(
                Point(*add_vectors(frame.point, -self.frame.yaxis * self.width)),
                self.frame.xaxis,
                self.frame.zaxis,
            ),
            Frame(frame.point, -self.frame.yaxis, self.frame.zaxis),  # small face at start point
            Frame(
                Point(*(frame.point + self.frame.xaxis * self.blank_length + self.frame.zaxis * self.height)),
                -self.frame.yaxis,
                -self.frame.zaxis,
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
        vertices, _ = self.blank.to_vertices_and_faces()
        x = [p.x for p in vertices]
        y = [p.y for p in vertices]
        z = [p.z for p in vertices]
        return min(x), min(y), min(z), max(x), max(y), max(z)

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

    def __str__(self):
        return "Beam {:.3f} x {:.3f} x {:.3f} at {}".format(
            self.width,
            self.height,
            self.length,
            self.frame,
        )

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
        x_vector = centerline.vector
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        if y_vector.length < DEFAULT_TOLERANCE:
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

    def add_features(self, features):
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self.features.extend(features)

    def remove_features(self, features=None):
        """Removes a feature from the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self.features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self.features = [f for f in self.features if f not in features]

    def add_blank_extension(self, start, end, joint_key=None):
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

    def remove_blank_extension(self, joint_key):
        """Removes a blank extension from the beam.

        Parameters
        ----------
        joint_key : int
            The key of the joint which required this extension.

        """
        del self._blank_extensions[joint_key]

    def _resolve_blank_extensions(self):
        """Returns the max amount by which to extend the beam at both ends."""
        start = 0.0
        end = 0.0
        for s, e in self._blank_extensions.values():
            start = max(start, s)
            end = max(end, e)
        return start, end

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
            ds = tmin * self.length  # should be negative
        elif side == "end":
            tmax = max(x.keys())
            de = (tmax - 1.0) * self.length
        return -ds, de

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
