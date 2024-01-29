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
    """Represents a X-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `XHalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_key : str
        The key of the main beam.
    cross_beam_key : str
        The key of the cross beam.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.


    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(XHalfLapJoint, self).__init__(frame, key)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = beam_a.key if beam_a else None
        self.beam_b_key = beam_b.key if beam_b else None
        self.flip_lap_side = flip_lap_side  # Decide if Direction of beam_a or beam_b
        self.features = []
        self.cut_plane_bias = cut_plane_bias
        self.features = []

    @property
    def data(self):
        data_dict = {
            "beam_a": self.beam_a_key,
            "beam_b": self.beam_b_key,
            "cut_plane_bias": self.cut_plane_bias,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], cut_plane_bias=value["cut_plane_bias"])
        instance.beam_a_key = value["beam_a"]
        instance.beam_b_key = value["beam_b"]
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
        point_cut = midpoint_point_point(int_a, int_b)

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

        return plane_cut, cutplane_vector_a, cutplane_vector_b

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        """Sorts the Beam Face Planes according to the Cut Plane"""
        frames = beam.faces[:4]
        planes = []
        for i in frames:
            planes.append(Plane.from_frame(i))
        planes.sort(key=lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias):
        """Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        """
        int_points = []
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = i.point_at(bias)  # intersection_line_plane(i, plane_b
            point_top = Point(*point_top)
            point_bottom = Point(*point_bottom)
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

        if self.flip_lap_side:
            plane_cut_vector_a, plane_cut_vector_b = plane_cut_vector_b, plane_cut_vector_a

        # Get Beam Faces (Planes) in right order
        planes_a = self._sort_beam_planes(self.beam_a, plane_cut_vector_a)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_a

        planes_b = self._sort_beam_planes(self.beam_b, plane_cut_vector_b)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_b

        # Lines as Frame Intersections
        lines = []
        unbound_line = intersection_plane_plane(plane_a1, plane_b1, tol=1e-6)

        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a1, plane_b2)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a2, plane_b2)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a2, plane_b1)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        # Create Polyhedrons
        negative_polyhedron_beam_a = self._create_polyhedron(plane_a0, lines, self.cut_plane_bias)
        negative_polyhedron_beam_b = self._create_polyhedron(plane_b0, lines, self.cut_plane_bias)
        return negative_polyhedron_beam_a, negative_polyhedron_beam_b

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)

    def add_features(self):
        negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))
