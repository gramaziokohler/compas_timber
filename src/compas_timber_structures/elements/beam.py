"""
Classes for linear elements with a rectangular cross-section.

"""

import copy

import compas
import compas.geometry
from compas.datastructures.mesh import Mesh
from compas.geometry import Transformation
from compas.geometry.angles import angle_vectors
from compas.geometry.objects import Frame, Line, Point, Polygon, Vector
from compas.geometry.objects.plane import Plane


class Beam(object):
    def __init__(self, beam_end1, beam_end2, width=0.0, height=0.0, z_dir=None):
        self.__set_end1(beam_end1)  # BeamEnd object
        self.__set_end2(beam_end2)  # BeamEnd object
        self.width = width  # cross-section width, float
        self.height = height  # cross-section height, float
        self.__set_z_vec(z_dir)  # cross-section height direction, compas Vector, must be perpendicular to centreline
        self.userdictionary = {}
        self.sides = [BeamSide(self, i) for i in range(6)]  # generate BeamSide objects

    def __get_end1(self):
        return self.__end1

    def __set_end1(self, beam_end):
        if beam_end:
            self.__end1 = beam_end
            beam_end.beam = self
    end1 = property(__get_end1, __set_end1)

    def __get_end2(self):
        return self.__end2

    def __set_end2(self, beam_end):
        if beam_end:
            self.__end2 = beam_end
            beam_end.beam = self
    end2 = property(__get_end2, __set_end2)

    def __get_z_vec(self):
        return self.__z_vec

    def __set_z_vec(self, vec_coordinates):
        # vec_coordinates: (x,y,z) tuple
        if not vec_coordinates:
            return None
        elif None in vec_coordinates:
            return None
        else:
            vec = Vector(*vec_coordinates)
        self.__z_vec = self.__correct_z(vec)
    z_vec = property(__get_z_vec, __set_z_vec)

    def __correct_z(self, vec):
        """
        vec: compas Vector
        z_vec: must be at all times perpendicular to the centreline (x_vec)
        """
        if vec.length < 1e-4:
            # TODO: why woudl this happen???
            return None
        a = angle_vectors(vec, self.x_vec, True)

        tol = 1e-8
        angtol = 0.01
        if a < tol or a > 180 - angtol:
            vec = Vector(vec[2], vec[0], vec[1])
            print("Beam.__correct_z: vector parallel to centreline! I swapped its components (x,y,z) -> (z,x,y)!")

        vec.unitize()
        x = self.x_vec
        x.unitize()
        y = x.cross(vec)
        y.unitize()
        z = x.cross(y*-1)
        return z

    @property
    def x_vec(self):
        """
        vector of the centreline
        """
        v = self.centreline.vector
        v.unitize()
        return v

    @property
    def y_vec(self):
        """
        cross-section vector in the 'width direction', must be perpendicular to the centreline (x_vec) and z_vec
        """
        return self.z_vec.cross(self.x_vec)

    @property
    def frame(self):
        return Frame(self.midpt, self.x_vec, self.y_vec)

    def transform(self, to_frame):
        """
        Transform end points and z from current frame to given frame
        """
        T = Transformation.from_frame_to_frame(self.frame, to_frame)
        ps = copy(self.end1.pt)
        pe = copy(self.end2.pt)
        z = copy(self.z_vec)
        ps.transform(T)
        pe.transform(T)
        z.transform(T)
        self.end1.pt = ps
        self.end2.pt = pe
        self.z_vec = z

    def move_endpoint(self, end, new_pt):
        end.pt = new_pt
        # that's it - the rest happens automatically

    def __mid_two_points__(self, p1, p2):
        return Point((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, (p1[2] + p2[2])/2)

    @property
    def midpt(self):
        return self.__mid_two_points__(self.end1.pt, self.end2.pt)

    @property
    def centreline(self):
        return Line(self.end1.pt, self.end2.pt)

    @property
    def length(self):
        return self.end1.pt.distance_to_point(self.end2.pt)

    @property
    def edges(self):
        """
        4 edges parallel to centreline
        """
        c = self.corners_default
        return [Line(c[i], c[i+4]) for i in range(4)]

    @property
    def corners(self):
        """
        8 corners of the beam derived from cutting planes at both ends
        """
        plns = [self.end1.cut_pln, self.end2.cut_pln]
        # TODO: add errortrap if cut_pln.normal is perpendicular to edges/axis => no intersection between cut_pln and edge lines
        return [compas.geometry.intersection_line_plane((line.start, line.end), (pln.point, pln.normal), 1e-6) for pln in plns for line in self.edges]

    @property
    def corners_default(self):
        """
        8 corners of a beam as if it was a box
        """
        ps = self.end1.pt
        pe = self.end2.pt
        y = self.y_vec*(self.width/2)
        z = self.z_vec*(self.height/2)
        return [ps + y + z,
                ps - y + z,
                ps - y - z,
                ps + y - z,
                pe + y + z,
                pe - y + z,
                pe - y - z,
                pe + y - z]

    @property
    def mesh_faces_quad(self):
        return [
            (0, 4, 7, 3),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
            (0, 1, 2, 3),
            (4, 5, 6, 7)
        ]

    @property
    def mesh_faces_tri(self):
        return [
            [2, 1, 0],
            [3, 2, 0],
            [6, 2, 3],
            [7, 6, 3],
            [5, 6, 7],
            [4, 5, 7],
            [1, 5, 4],
            [0, 1, 4],
            [1, 2, 6],
            [5, 1, 6],
            [3, 0, 4],
            [7, 3, 4]
        ]

    @property
    def mesh(self):
        return Mesh.from_vertices_and_faces(self.corners, self.mesh_faces_tri)


class BeamEnd(object):
    def __init__(self, point=(None, None, None)):
        self.pt = Point(*point)  # coordinates
        # self.beam = None #Beam object --> trying to avoid these refs!
        self.connection = None
        self.userdictionary = {}

    #     self.__cut_pln = None

    # def __get_cut_pln(self):
    #     if self.__cut_pln: return self.__cut_pln
    #     else: return Plane(self.pt, self.beam.x_vec)

    # def __set_cut_pln(self, custom_pln):
    #     self.__cut_pln = custom_pln

    # cut_pln = property(__get_cut_pln, __set_cut_pln)


class BeamSide(object):
    def __init__(self, beam, side_nr=-1):
        self.beam = beam  # --> trying to avoid these refs!
        self.nr = side_nr
        if side_nr not in range(6):
            raise KeyError
        self.userdictionary = {}

        """
        side numbering:
            0    y_dir    w
            1    z_dir    h
            2   -y_dir   -w
            3   -z_dir   -h
            4   front side
            5   back side
        """

    @property
    def vec(self):
        # // => normal to the side pointing outwards
        y = self.beam.y_vec
        z = self.beam.z_vec
        return [y, z, y*-1, z*-1][self.nr]

    @property
    def vec_scaled(self):
        # // => normal to the side pointing outwards, length according to beam's dimension
        # // => side 4 and 5 added by mhelmrei, 29.06.2018
        x = self.beam.x_vec*(self.beam.length)
        y = self.beam.y_vec*(self.beam.width/2)
        z = self.beam.z_vec*(self.beam.height/2)
        return [y, z, y*-1, z*-1, x*-1, x][self.nr]

    @property
    def dim(self):
        # // => distance to centreline
        d = self.beam.length
        w = self.beam.width/2
        h = self.beam.height/2
        return [w, h, -w, -h, -d, d][self.nr]

    @property
    def corner_indices(self):
        return [
            [0, 4, 7, 3],
            [1, 5, 4, 0],
            [2, 6, 5, 1],
            [3, 7, 6, 2],
            [0, 1, 2, 3],
            [4, 5, 6, 7]
        ][self.nr]

    @property
    def corners(self):
        c = self.beam.corners
        return [c[i] for i in self.corner_indices]

    @property
    def pln(self):
        pt = (self.beam.midpt+self.vec_scaled)
        origin = [pt[0], pt[1], pt[2]]
        v = (self.vec)
        vector = [v.x, v.y, v.z]
        return Plane(origin, vector)

    @property
    def frame(self):
        pt = (self.beam.midpt+self.vec_scaled)
        origin = [pt[0], pt[1], pt[2]]
        x_vec = self.beam.x_vec

        _y = self.beam.y_vec
        _z = self.beam.z_vec
        y_vec = [_z, _y*-1, _z*-1, _y][self.nr]

        return Frame(origin, x_vec, y_vec)

    @property
    def outline(self):
        return Polygon(self.corners)


if __name__ == "__main__":

    e1 = BeamEnd([0, 0, 0])
    e2 = BeamEnd([1, 0, 1])
    v = ([0, 0, 2])

    B = Beam(e1, e2, 0.1, 0.2, v)

    # B.end1.cut_pln_default(True)
    # B.end2.cut_pln_default(True)
    # print B.sides[1].outline
