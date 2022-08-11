import copy
from collections import deque

from compas.datastructures.assembly import Part
from compas.datastructures.assembly.part import BrepGeometry
from compas.datastructures.assembly.part import MeshGeometry
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
from compas.geometry import close
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point

from compas_timber.parts.exceptions import BeamCreationException
from compas_timber.utils.helpers import close

# TODO: update to global compas PRECISION
ANGLE_TOLERANCE = 1e-3  # [radians]
DEFAULT_TOLERANCE = 1e-6


def _create_box(width, height, length):
    # mesh reference point is always worldXY, geometry is transformed to actual frame on Beam.geometry
    # TODO: Alternative: Add frame information to MeshGeometry, otherwise Frame is only implied by the vertex values
    boxframe = Frame.worldXY()
    length_offset = boxframe.xaxis * length * 0.5
    boxframe.point += length_offset
    return Box(boxframe, length, width, height)


def _create_mesh_shape(width, height, length):
    return MeshGeometry(_create_box(width, height, length))


def _create_brep_shape(width, height, length):
    # Create a Rhino.Geometry.Box
    brep_box = Brep.from_box(_create_box(width, height, length))
    return BrepGeometry(brep_box)


class Beam(Part):
    """A class to represent timber beams (studs, slats, etc.), straight with rectangular cross-sections.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`.
        A local coordinate system of the beam:
        Origin is located at the starting point of the centerline.
        x-axis corresponds to the centerline (major axis), usually also the fibre direction in solid wood beams.
        y-axis corresponds to the width of the cross-section, usually the smaller dimension.
        z-axis corresponds to the height of the cross-section, usually the larger dimension.

    width : float.
        Width of the cross-section.
    height : float.
        Height of the cross-section.
    length : float.
        Length of the beam.
    geometry_type : string
        Type of the output geometry: 'brep' for Brep or 'mesh' for mesh.

    Attributes
    ----------

    centerline: :class:``compas.geometry.Line`

    """

    SHAPE_FACTORIES = {
        "mesh": _create_mesh_shape,
        "brep": _create_brep_shape,
    }

    def __init__(self, frame, width, height, length, geometry_type, **kwargs):
        geometry = self._create_beam_shape_from_params(width, height, length, geometry_type)
        super(Beam, self).__init__(geometry=geometry, frame=frame)
        self.frame = frame  # TODO: add setter so that only that makes sure the frame is orthonormal --> needed for comparisons
        self.width = width
        self.height = height
        self.length = length
        self.geometry_type = geometry_type
        self.assembly = None

    @staticmethod
    def _create_beam_shape_from_params(width, height, length, geometry_type):
        try:
            factory = Beam.SHAPE_FACTORIES[geometry_type]
            return factory(width, height, length)
        except KeyError:
            raise BeamCreationException("Expected one of {} got instaed: {}".format(Beam.SHAPE_FACTORIES.keys(), geometry_type))

    def __str__(self):
        return "Beam %s x %s x %s at %s" % (self.width, self.height, self.length, self.frame)

    def __copy__(self, *args, **kwargs):
        return self.copy()

    def __deepcopy__(self, memodict):
        # Having a refernce to assembly here causes very weird behavior
        # when copying using data.copy()
        self.assembly = None
        return self.copy()

    def is_identical(self, other):
        tol = self.tol
        return (
            isinstance(other, Beam)
            and close(self.width, other.width, tol)
            and close(self.height, other.height, tol)
            and close(self.length, other.length, tol)
            and self.frame == other.frame
            # TODO: skip joints and features ?
        )

    @property
    def tolerance(self):
        return getattr(self.assembly, "tol", DEFAULT_TOLERANCE)

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

    @classmethod
    def from_data(cls, data):
        instance = cls(**data)
        instance.data = data
        return instance

    @classmethod
    def from_centerline(cls, centerline, width, height, z_vector=None, geometry_type="mesh"):
        """
        Define the beam from its centerline.
        z_vector: a vector indicating the height direction (z-axis) of the cross-section. If not specified, a default will be used.
        """
        x_vector = centerline.vector
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        frame = Frame(centerline.start, x_vector, y_vector)
        length = centerline.length

        return cls(frame, width, height, length, geometry_type)

    @classmethod
    def from_endpoints(cls, point_start, point_end, width, height, z_vector=None):

        x_vector = Vector.from_start_end(point_start, point_end)
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        frame = Frame(point_start, x_vector, y_vector)
        length = distance_point_point(point_start, point_end)

        return cls(frame, width, height, length)

    ### main methods and properties ###
    @property
    def faces(self):
        """
        Face frames of the beam's base shape (box) are numbered relative to the beam's coordinate system
        """
        return [
            Frame(Point(*add_vectors(self.midpoint, self.frame.yaxis * self.width * 0.5)), self.frame.xaxis, -self.frame.zaxis),
            Frame(Point(*add_vectors(self.midpoint, -self.frame.zaxis * self.height * 0.5)), self.frame.xaxis, -self.frame.yaxis),
            Frame(Point(*add_vectors(self.midpoint, -self.frame.yaxis * self.width * 0.5)), self.frame.xaxis, self.frame.zaxis),
            Frame(Point(*add_vectors(self.midpoint, self.frame.zaxis * self.height * 0.5)), self.frame.xaxis, self.frame.yaxis),
            Frame(self.frame.point, -self.frame.yaxis, self.frame.zaxis),  # small face at start point
            Frame(Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length)), self.frame.yaxis, self.frame.zaxis),  # small face at end point
        ]

    ### GEOMETRY ###
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
    def midpoint(self):
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length * 0.5))

    def move_endpoint(self, vector=Vector(0, 0, 0), which_endpoint="start"):
        # create & apply a transformation
        """
        which_endpoint: 'start' or 'end' or 'both'
        """
        z = self.frame.zaxis
        ps = self.__centerline_start
        pe = self.__centerline_end
        if which_endpoint in ("start", "both"):
            ps = add_vectors(ps, vector)
        if which_endpoint in ("end", "both"):
            pe = add_vectors(pe, vector)
        x = Vector.from_start_end(ps, pe)
        y = Vector(*cross_vectors(x, z)) * -1.0
        frame = Frame(ps, x, y)
        self.frame = frame
        self.length = distance_point_point(ps, pe)
        return

    def extend_length(self, d, option="both"):
        """
        options: 'start', 'end', 'both'
        """
        if option in ("start", "both"):
            pass  # move frame's origin by -d
        if option == "end":
            pass  # change length by d
        if option == "both":
            pass  # chane lenth by 2d
        return

    def rotate_around_centerline(self, angle, clockwise=False):
        # create & apply a transformation
        pass

    def align_z(self, vector):
        y_vector = Vector(*cross_vectors(self.frame.xaxis, vector)) * -1.0
        frame = Frame(self.frame.point, self.frame.xaxis, y_vector)
        self.frame = frame
        return

    ### JOINTS ###

    def _get_joint_keys(self):
        n = self.assembly.graph.neighbors[self.key]
        return [k for k in n if self.assembly.node_attribute("type") == "joint"]  # just double-check in case the joint-node would be somehow connecting to smth else in the graph

    @property
    def joints(self):
        return [self.assembly.find_by_key(key) for key in self._get_joint_keys]

    ### FEATURES ###

    @property
    def has_features(self):
        return len(self.features) > 0

    ### hidden helpers ###
    @staticmethod
    def _calculate_z_vector_from_centerline(centerline_vector):
        z = Vector(0, 0, 1)
        if angle_vectors(z, centerline_vector) < ANGLE_TOLERANCE:
            z = Vector(1, 0, 0)
        return z

    def endpoint_closest_to_point(self, point):
        ps = self.centerline_start
        pe = self.centerline_end
        ds = point.distance_to_point(ps)
        de = point.distance_to_point(pe)

        if ds <= de:
            return ["start", ps]
        else:
            return ["end", pe]

if __name__ == "__main__":
    b = Beam(Frame.worldXY(), 10, 5, 13, "brep")
    print(b.geometry)
