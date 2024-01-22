from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import length_vector
from compas.geometry import midpoint_point_point

from compas_timber.parts import MillVolume
from compas_timber.utils import intersection_line_line_3D

from .joint import Joint
from .solver import JointTopology


class XHalfLapJoint(Joint):
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, beam_a=None, beam_b=None, cut_plane_choice=None, cut_plane_bias = 0.5, frame=None, key=None):
        super(XHalfLapJoint, self).__init__(frame, key)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = beam_a.key if beam_a else None
        self.beam_b_key = beam_b.key if beam_b else None
        self.cut_plane_choice = cut_plane_choice  # Decide if Direction of beam_a or beam_b
        self.features = []
        self.cutplane = []
        self.sorted_frames_a = []
        self.sorted_frames_b = []
        self.sorted_planes_a = []
        self.sorted_planes_b = []
        self.operation_plane_a = []
        self.operation_plane_b = []
        self.cut_plane_bias = cut_plane_bias

    @property
    def data(self):
        data_dict = {
            "beam_a": self.beam_a_key,
            "beam_b": self.beam_b_key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], cutoff=value["cut_plane_choice"])
        instance.beam_a_key = value["beam_a"]
        instance.beam_b_key = value["beam_b"]
        instance.cut_plane_choice = value["cut_plane_choice"]
        return instance

    @property
    def joint_type(self):
        return "X-HalfLap"

    @property
    def beams(self):
        return [self.beam_a, self.beam_b]

    def _cutplane(self):
        # Find the Point for the Cut Plane
        centerline_a = self.beam_a.centerline
        centerline_b = self.beam_b.centerline
        max_distance = float("inf")
        int_a, int_b = intersection_line_line_3D(centerline_a, centerline_b, max_distance)
        int_a, _ = int_a
        int_b, _ = int_b
        point_cut = int_a * self.cut_plane_bias + int_b*(1-self.cut_plane_bias)

        # Vector Cross Product
        beam_a_start = self.beam_a.centerline_start
        beam_b_start = self.beam_b.centerline_start
        beam_a_end = self.beam_a.centerline_end
        beam_b_end = self.beam_b.centerline_end
        centerline_vec_a = Vector.from_start_end(beam_a_start, beam_a_end)
        centerline_vec_b = Vector.from_start_end(beam_b_start, beam_b_end)
        plane_cut = Plane.from_point_and_two_vectors(point_cut, centerline_vec_a, centerline_vec_b)

        # Flip Cut Plane if its Normal Z-Coordinate is positive
        if plane_cut[1][2] > 0:
            plane_cut[1] = plane_cut[1] * -1

        # Cutplane Normal Vector pointing from a and b to Cutplane Origin
        cutplane_vector_a = Vector.from_start_end(int_a, point_cut)
        cutplane_vector_b = Vector.from_start_end(int_b, point_cut)

        # If Centerlines crossing, take the Cutplane Normal
        if length_vector(cutplane_vector_a) < 1e-6:
            cutplane_vector_a = plane_cut.normal
        if length_vector(cutplane_vector_b) < 1e-6:
            cutplane_vector_b = plane_cut.normal * -1

        self.cutplane = plane_cut

        return plane_cut, cutplane_vector_a, cutplane_vector_b

    @staticmethod
    def _sort_beam_planes_old(beam, cutplane_vector):  # TODO delete this if the new function works!!!
        frames = beam.faces[:4]
        planes = []
        planes_angles = []
        for i in frames:
            planes.append(Plane.from_frame(i))
            planes_angles.append(angle_vectors(cutplane_vector, i.normal))
        planes_angles, planes = zip(*sorted(zip(planes_angles, planes)))
        return planes

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Reorders the Beam Planes based on which Plane is the Operation Face
        frames = beam.faces[:4]
        angles = []
        for i in frames:
            angles.append(angle_vectors(cutplane_vector, i.normal))
        min_item = angles.index(min(angles))  # smallest normal angle
        frames_sorted = frames[min_item:] + frames[:min_item]  # rotate the list
        frames_sorted.append(beam.faces[4])  # add Frame 5
        frames_sorted.append(beam.faces[5])  # add Frame 6
        planes_sorted = []
        for i in frames_sorted:
            planes_sorted.append(Plane.from_frame(i))
        return frames_sorted, planes_sorted, min_item

    @staticmethod
    def _create_polyhedron(plane_a, plane_b, lines):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = intersection_line_plane(i, plane_b)
            int_points.append(point_top)
            int_points.append(point_bottom)

        # Step 2: Check if int_points Order results in an inward facing Polyhedron
        test_face_vector1 = Vector.from_start_end(int_points[0], int_points[2])
        test_face_vector2 = Vector.from_start_end(int_points[0], int_points[6])
        test_face_normal = Vector.cross(test_face_vector1, test_face_vector2)
        check_vector = Vector.from_start_end(int_points[0], int_points[1])
        # Flip int_points Order if needed
        if angle_vectors(test_face_normal, check_vector) < 1:
            a, b, c, d, e, f, g, h = int_points
            int_points = b, a, d, c, f, e, h, g

        # Step 3: Create a Hexahedron with 6 Faces from the 8 Points
        return Polyhedron(
            int_points,
            [
                [1, 7, 5, 3],  # top
                [0, 2, 4, 6],  # bottom
                [1, 3, 2, 0],  # left
                [3, 5, 4, 2],  # back
                [5, 7, 6, 4],  # right
                [7, 1, 0, 6],  # front
            ],
        )

    def _create_negative_volumes(self):
        # Get Cut Plane
        plane_cut, plane_cut_vector_a, plane_cut_vector_b = self._cutplane()

        # Get Beam Faces (Planes) in right order
        self.sorted_frames_a, self.sorted_planes_a, self.operation_plane_a = self._sort_beam_planes(
            self.beam_a, plane_cut_vector_a
        )
        plane_a0, plane_a1, plane_a2, plane_a3, plane_a4, plane_a5 = self.sorted_planes_a

        self.sorted_frames_b, self.sorted_planes_b, self.operation_plane_b = self._sort_beam_planes(
            self.beam_b, plane_cut_vector_b
        )
        plane_b0, plane_b1, plane_b2, plane_b3, plane_b4, plane_b5 = self.sorted_planes_b

        # Lines as Frame Intersections
        lines = []
        x = intersection_plane_plane(plane_a1, plane_b1)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a1, plane_b3)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a3, plane_b3)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a3, plane_b1)
        lines.append(Line(x[0], x[1]))

        # Create Polyhedrons
        negative_polyhedron_beam_a = self._create_polyhedron(plane_a0, plane_cut, lines)
        negative_polyhedron_beam_b = self._create_polyhedron(plane_b0, plane_cut, lines)
        return negative_polyhedron_beam_a, negative_polyhedron_beam_b

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)

    def add_features(self):
        negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))
