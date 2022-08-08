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

# TODO: update to global compas PRECISION
tol_angle = 1e-3  # [radians]


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

    operations = ["union" "difference" "intersection" "planar_trim"]

    def __init__(self, frame, length, width, height):
        super(Beam, self).__init__()
        self.frame = frame  # TODO: add setter so that only that makes sure the frame is orthonormal --> needed for comparisons
        self.width = width
        self.height = height
        self.length = length
        self.assembly = None

    def __str__(self):
        return "Beam %s x %s x %s at %s" % (
            self.width,
            self.height,
            self.length,
            self.frame,
        )

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
    def tol(self):
        return getattr(self.assembly, "tol", 1e-6)

    @property
    def data(self):
        """
        Workaround: overrides Part.data since serialization of Beam using Data.from_data is not supported.
        """
        data = {
            "attributes": self.attributes,
            "assembly": self.assembly,
            "key": self.key,
            "frame": self.frame,
            "shape": self.shape,
            "features": [(shape, operation) for shape, operation in self.features],
            "transformations": [T.data for T in self.transformations],
        }
        return data

    @data.setter
    def data(self, data):
        """
        Workaround: overrides Part.data.setter since de-serialization of Beam using Data.from_data is not supported.
        """
        self.attributes.update(data["attributes"] or {})
        self.assembly = data["assembly"]
        self.key = data["key"]
        self.frame = data["frame"]
        self.shape = data["shape"]
        self.features = [(shape, operation) for shape, operation in data["features"]]
        self.transformations = deque(
            [Transformation.from_data(T) for T in data["transformations"]]
        )

    @classmethod
    def from_frame(cls, frame, width, height, length):
        # needed? same as init
        return cls(frame, length, width, height)

    @classmethod
    def from_centreline(cls, centreline, z_vector, width, height):
        """
        Define the beam from its centreline.
        z_vector: a vector indicating the height direction (z-axis) of the cross-section. If not specified, a default will be used.
        """
        x_vector = centreline.vector
        if not z_vector:
            z_vector = cls.__default_z(x_vector)
        y_vector = Vector(*cross_vectors(x_vector, z_vector)) * -1.0
        frame = Frame(centreline.start, x_vector, y_vector)
        length = centreline.length

        return cls(frame, length, width, height)

    @classmethod
    def from_endpoints(cls, point_start, point_end, z_vector, width, height):

        line = Line(point_start, point_end)

        return cls.from_centreline(line, z_vector, width, height)

    ### main methods and properties ###

    def copy(self):
        # TODO: temp workaround, inherited copy method doesn't work
        beam = Beam(self.frame, self.length, self.width, self.height)
        beam.features = self.features
        return beam

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
        if side_index == 0:
            return Frame(
                Point(
                    *add_vectors(self.frame.point, self.frame.yaxis * self.width * 0.5)
                ),
                self.frame.xaxis,
                -self.frame.zaxis,
            )
        if side_index == 1:
            return Frame(
                Point(
                    *add_vectors(
                        self.frame.point, -self.frame.zaxis * self.height * 0.5
                    )
                ),
                self.frame.xaxis,
                -self.frame.yaxis,
            )
        if side_index == 2:
            return Frame(
                Point(
                    *add_vectors(self.frame.point, -self.frame.yaxis * self.width * 0.5)
                ),
                self.frame.xaxis,
                self.frame.zaxis,
            )
        if side_index == 3:
            return Frame(
                Point(
                    *add_vectors(self.frame.point, self.frame.zaxis * self.height * 0.5)
                ),
                self.frame.xaxis,
                self.frame.yaxis,
            )
        if side_index == 4:
            return Frame(self.frame.point, -self.frame.yaxis, self.frame.zaxis)
        if side_index == 5:
            return Frame(
                Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length)),
                self.frame.yaxis,
                self.frame.zaxis,
            )

    @property
    def centreline(self):
        return Line(self.__centreline_start, self.__centreline_end)

    @property
    def shape(self):
        """
        Base shape of the beam, i.e. box with no features.
        """
        boxframe = Frame(
            self.frame.point - self.frame.yaxis*self.width*0.5 - self.frame.zaxis*self.height*0.5,
            self.frame.xaxis,
            self.frame.yaxis,
        )
        return Box(boxframe, self.length, self.width, self.height)

    @shape.setter
    def shape(self, box):
        # TODO: temp error catcher: calling Beam.shape throws an error in Part ("readonly attribute")
        pass

    @property
    def geometry(self, geometry_representation="brep"):
        """
        Geometry of the beam with all features (e.g. trims, cuts, notches, holes etc.)
        geometry_representation: 'mesh', 'brep'
        """
        # apply all self.features to the self.shape through boolean operations.
        # I want to choose geometry representation (mesh, brep etc.)

        pass

    ### GEOMETRY ###

    @property
    def __centreline_start(self):
        return self.frame.point

    @property
    def __centreline_end(self):
        return Point(*add_vectors(self.frame.point, self.frame.xaxis * self.length))

    @property
    def long_edges(self):
        y = self.frame.yaxis
        z = self.frame.zaxis
        w = self.width*0.5
        h = self.height*0.5
        ps = self.__centreline_start
        pe = self.__centreline_end


        return [Line(ps+v, pe+v) for v in 
                                                        ( y*w+z*h, 
                                                         -y*w+z*h,  
                                                         -y*w-z*h,
                                                          y*w-z*h,)]

    @property
    def midpoint(self):
        return Point(
            *add_vectors(self.frame.point, self.frame.xaxis * self.length * 0.5)
        )

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
    
    def extend_ends(self, d_start, d_end):
        """
        Extensions at the start of the centerline should have a negative value.
        Extenshions at the end of the centerline should have a positive value.
        Otherwise the centerline will be shortend, not extended.
        """
        ps = self.__centreline_start
        pe = self.__centreline_end
        self.frame.point += self.frame.xaxis*d_start
        self.length += -d_start+d_end


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
        return [
            k for k in n if self.assembly.node_attribute("type") == "joint"
        ]  # just double-check in case the joint-node would be somehow connecting to smth else in the graph

    @property
    def joints(self):
        return [self.assembly.find_by_key(key) for key in self._get_joint_keys]

    ### FEATURES ###

    def add_feature(self, shape, operation):
        """
        shape: compas geometry
        operation: 'bool_union', 'bool_difference', 'bool_intersection', 'trim'
        """
        # TODO: add some descriptor attribute to identify the source/type/character of features later?
        self.features.append((shape, operation))

    def clear_features(self):
        self.features = []
        return

    @property
    def has_features(self):
        if len(self.features) == 0:
            return False
        else:
            return True

    ### hidden helpers ###
    @staticmethod
    def __default_z(centreline_vector):
        z = Vector(0, 0, 1)
        if angle_vectors(z, centreline_vector) < tol_angle:
            z = Vector(1, 0, 0)
        return z

    def endpoint_closest_to_point(self, point):
        ps = self.__centreline_start
        pe = self.__centreline_end
        ds = point.distance_to_point(ps)
        de = point.distance_to_point(pe)

        if ds <= de:
            return ["start", ps]
        else:
            return ["end", pe]


if __name__ == "__main__":
    b = Beam()
