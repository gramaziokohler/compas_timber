from collections import deque

from compas.datastructures.assembly import Part
from compas.geometry import Box
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

from compas_timber.utils.helpers import close
from compas_timber.parts.exceptions import BeamCreationException

# TODO: not to do
from compas_rhino.conversions import box_to_rhino
from Rhino.Geometry import Brep


# TODO: update to global compas PRECISION
ANGLE_TOLERANCE = 1e-3  # [radians]
DEFAULT_TOLERANCE = 1e-6


def _create_mesh_geometry(length, width, height):
    # mesh reference point is always worldXY, geometry is transformed to actual frame on Beam.geometry
    # TODO: Alternative: Add frame information to MeshGeometry, otherwise Frame is only implied by the vertex values
    return MeshGeometry(Box(Frame.worldXY(), length, width, height))


def _create_brep_geometry(length, width, height):
    boxframe = Frame.worldXY()

    # Frame defines the start corner in RhinoBox, adjust height and width ot center
    width_offset = boxframe.yaxis * width * 0.5
    height_offset = boxframe.zaxis * height * 0.5
    length_offset = boxframe.xaxis * length * 0.5
    boxframe.point -= width_offset + height_offset + length_offset

    rhino_box = box_to_rhino(Box(boxframe, length, width, height))
    return BrepGeometry(rhino_box.ToBrep())


class Beam(Part):
    """A class to represent timber beams (studs, slats, etc.) with rectangular cross-sections.
    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`.
        A local coordinate system of the beam:
        Origin is located at the starting point of the centreline.
        x-axis corresponds to the centreline (major axis), usually also the fibre direction in solid wood beams.
        y-axis corresponds to the width of the cross-section, usually the smaller dimension.
        z-axis corresponds to the height of the cross-section, usually the larger dimension.

    width : float.
        Width of the cross-section
    height : float.
        Height of the cross-section

    Attributes
    ----------

    length : float.
        Length of the beam.

    centreline: :class:``compas.geometry.Line`
    """

    GEOMETRY_FACTORIES = {
        "mesh": _create_mesh_geometry,
        "brep": _create_brep_geometry,
    }

    def __init__(self, frame, length, width, height, geometry_type):
        self.frame = frame  # TODO: add setter so that only that makes sure the frame is orthonormal --> needed for comparisons
        self.width = width
        self.height = height
        self.length = length
        self.assembly = None

        geometry = self._create_geometry_from_params(length, width, height, geometry_type)
        super(Beam, self).__init__(geometry=geometry, frame=frame)

    @staticmethod
    def _create_geometry_from_params(length, width, height, geometry_type):
        try:
            factory = Beam.GEOMETRY_FACTORIES[geometry_type]
            return factory(length, width, height)
        except KeyError:
            raise BeamCreationException("Expected one of {} got instaed: {}".format(Beam.GEOMETRY_FACTORIES.keys(), geometry_type))

    def __str__(self):
        return "Beam %s x %s x %s at %s" % (self.width, self.height, self.length, self.frame)

    def __copy__(self, *args, **kwargs):
        return self.copy()

    def __eq__(self, other):
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
        data = {
            "width": self.width,
            "height": self.height,
            "length": self.length,
        }
        data.update(super(Beam, self).data)
        return data

    @data.setter
    def data(self, data):
        """
        Workaround: overrides Part.data.setter since de-serialization of Beam using Data.from_data is not supported.
        """
        super(Beam, self).data = data
        self.width = data["width"]
        self.height = data["height"]
        self.length = data["length"]

    @classmethod
    def from_centreline(cls, centreline, width, height, z_vector=None, geometry_type="mesh"):
        """
        Define the beam from its centreline.
        z_vector: a vector indicating the height direction (z-axis) of the cross-section. If not specified, a default will be used.
        """
        x_vector = centreline.vector
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        frame = Frame(centreline.midpoint, x_vector, y_vector)
        length = centreline.length

        return cls(frame, length, width, height, geometry_type)

    @classmethod
    def from_endpoints(cls, point_start, point_end, width, height, z_vector=None):

        x_vector = Vector.from_start_end(point_start, point_end)
        z_vector = z_vector or cls._calculate_z_vector_from_centerline(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        frame = Frame(point_start, x_vector, y_vector)
        length = distance_point_point(point_start, point_end)

        return cls(frame, length, width, height)

    ### main methods and properties ###

    def side_frame(self, side_index):
        """
        Side index: sides of the beam's base shape (box) are numbered relative to the beam's coordinate system:
        0: +y (side's frame normal is equal to the beam's Y positive direction)
        1: +z
        2: -y
        3: -z
        4: -x (side at the starting end)
        5: +x (side at the end of the beam)
        """
        sides = [
            Frame(Point(*add_vectors(self.frame.point, self.frame.yaxis * self.width * 0.5)), self.frame.xaxis, -self.frame.zaxis),
            Frame(Point(*add_vectors(self.frame.point, -self.frame.zaxis * self.height * 0.5)), self.frame.xaxis, -self.frame.yaxis),
            Frame(Point(*add_vectors(self.frame.point, -self.frame.yaxis * self.width * 0.5)), self.frame.xaxis, self.frame.zaxis),
            Frame(Point(*add_vectors(self.frame.point, self.frame.zaxis * self.height * 0.5)), self.frame.xaxis, self.frame.yaxis),
            Frame(self.frame.point, -self.frame.yaxis, self.frame.zaxis),
            Frame(Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length)), self.frame.yaxis, self.frame.zaxis),
        ]

        try:
            return sides[side_index]
        except IndexError:
            return None

    @property
    def centreline(self):
        return Line(self.__centreline_start, self.__centreline_end)

    ### GEOMETRY ###

    @property
    def __centreline_start(self):
        return self.frame.point

    @property
    def __centreline_end(self):
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
        ps = self.__centreline_start
        pe = self.__centreline_end
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

    def rotate_around_centreline(self, angle, clockwise=False):
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
    def _calculate_z_vector_from_centerline(centreline_vector):
        z = Vector(0, 0, 1)
        if angle_vectors(z, centreline_vector) < ANGLE_TOLERANCE:
            z = Vector(1, 0, 0)
        return z


if __name__ == "__main__":
    b = Beam(Frame.worldXY(), 10, 5, 13)
    print(b.geometry)
