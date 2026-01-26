from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane

from .joint import Joint
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class LapJoint(Joint):
    """Abstract Lap type joint with functions common to L-Lap, T-Lap, and X-Lap Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.

    Attributes
    ----------
    elements : list of :class:`~compas_timber.elements.Beam`
        The beams to be joined.
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.

    """

    @property
    def __data__(self):
        data = super(LapJoint, self).__data__
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(LapJoint, self).__init__(elements=(beam_a, beam_b), **kwargs)
        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self.features = []

        self._ref_side_index_a = None
        self._ref_side_index_b = None
        self._cutting_plane_a = None
        self._cutting_plane_b = None

    @property
    def beam_a(self):
        return self.element_a

    @property
    def beam_b(self):
        return self.element_b

    @property
    def ref_side_index_a(self):
        """The reference side index of the beam_a."""
        if self._ref_side_index_a is None:
            self._ref_side_index_a = self._get_beam_ref_side_index(self.beam_a, self.beam_b, self.flip_lap_side)
        return self._ref_side_index_a

    @property
    def ref_side_index_b(self):
        """The reference side index of the beam_b."""
        if self._ref_side_index_b is None:
            self._ref_side_index_b = self._get_beam_ref_side_index(self.beam_b, self.beam_a, self.flip_lap_side)
        return self._ref_side_index_b

    @property
    def cutting_plane_a(self):
        """The face of the beam_b that cuts the beam_a, as a plane."""
        if self._cutting_plane_a is None:
            self._cutting_plane_a = self._get_cutting_plane(self.beam_b, self.beam_a)
        return self._cutting_plane_a

    @property
    def cutting_plane_b(self):
        """The face of the beam_a that cuts the beam_b, as a plane."""
        if self._cutting_plane_b is None:
            self._cutting_plane_b = self._get_cutting_plane(self.beam_a, self.beam_b)
        return self._cutting_plane_b

    @staticmethod
    def _get_beam_ref_side_index(beam_a, beam_b, flip):
        """Returns the reference side index of beam_a with respect to beam_b."""
        # get the offset vector of the two centerlines, if any
        offset_vector = Vector.from_start_end(*intersection_line_line(beam_a.centerline, beam_b.centerline))
        cross_vector = beam_a.centerline.direction.cross(beam_b.centerline.direction)
        # flip the cross_vector if it is pointing in the opposite direction of the offset_vector
        if cross_vector.dot(offset_vector) < 0:
            cross_vector = -cross_vector
        ref_side_dict = beam_ref_side_incidence_with_vector(beam_a, cross_vector, ignore_ends=True)
        if flip:
            return max(ref_side_dict, key=ref_side_dict.get)
        return min(ref_side_dict, key=ref_side_dict.get)

    @staticmethod
    def _get_cutting_plane(beam_a, beam_b):
        """Returns the plane from beam_b that cuts beam_a."""
        ref_side_dict = beam_ref_side_incidence(beam_b, beam_a, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return Plane.from_frame(beam_a.ref_sides[ref_side_index])

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Sorts the Beam Face Planes according to the Cut Plane
        frames = beam.ref_sides[:4]
        planes = [Plane.from_frame(frame) for frame in frames]
        planes.sort(key=lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        # Find the line with the biggest length
        longest_line = max(lines, key=lambda line: line.length)
        plane = Plane(longest_line.point_at(bias), longest_line.direction)
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = intersection_line_plane(i, plane)
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

    def _create_negative_volumes(self, cut_plane_bias):
        assert len(self.elements) > 1, "LapJoint requires two elements."
        beam_a, beam_b = self.elements

        # Get Cut Plane
        plane_cut_vector = beam_a.centerline.vector.cross(beam_b.centerline.vector)
        # flip the plane normal if the cross_vector is pointing in the opposite direction of the offset_vector
        offset_vector = Vector.from_start_end(*intersection_line_line(beam_a.centerline, beam_b.centerline))
        if plane_cut_vector.dot(offset_vector) >= 0:
            plane_cut_vector = -plane_cut_vector

        # Get Beam Faces (Planes) in right order
        planes_a = self._sort_beam_planes(beam_a, plane_cut_vector)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_a

        planes_b = self._sort_beam_planes(beam_b, -plane_cut_vector)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_b

        # Lines as Frame Intersections
        lines = []
        pt_a = intersection_plane_plane_plane(plane_a1, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a1, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        # Create Polyhedrons
        negative_polyhedron_beam_a = self._create_polyhedron(plane_b0, lines, cut_plane_bias)
        negative_polyhedron_beam_b = self._create_polyhedron(plane_a0, lines, cut_plane_bias)

        if self.flip_lap_side:
            return negative_polyhedron_beam_b, negative_polyhedron_beam_a
        return negative_polyhedron_beam_a, negative_polyhedron_beam_b
