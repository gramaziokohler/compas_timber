from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane

from .joint import Joint


class LapJoint(Joint):
    """Abstract Lap type joint with functions common to L-Lap, T-Lap, and X-Lap Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an model.

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
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    """

    @property
    def __data__(self):
        data = super(LapJoint, self).__data__
        data["main_beam"] = self.main_beam_guid
        data["cross_beam"] = self.cross_beam_guid
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5):
        super(LapJoint, self).__init__()
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None
        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.beam_by_guid(self.main_beam_guid) if self.main_beam_guid else None
        self.cross_beam = model.beam_by_guid(self.cross_beam_guid) if self.cross_beam_guid else None

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Sorts the Beam Face Planes according to the Cut Plane
        frames = beam.faces[:4]
        planes = [Plane.from_frame(frame) for frame in frames]
        planes.sort(key=lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
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

    def get_main_cutting_frame(self):
        assert self.elements
        beam_a, beam_b = self.elements

        _, cfr = self.get_face_most_towards_beam(beam_a, beam_b)
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr

    def get_cross_cutting_frame(self):
        assert self.elements
        beam_a, beam_b = self.elements
        _, cfr = self.get_face_most_towards_beam(beam_b, beam_a)
        return cfr

    def _create_negative_volumes(self):
        assert self.elements
        beam_a, beam_b = self.elements

        # Get Cut Plane
        plane_cut_vector = beam_a.centerline.vector.cross(beam_b.centerline.vector)

        if self.flip_lap_side:
            plane_cut_vector = -plane_cut_vector

        # Get Beam Faces (Planes) in right order
        planes_main = self._sort_beam_planes(beam_a, plane_cut_vector)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_main

        planes_cross = self._sort_beam_planes(beam_b, -plane_cut_vector)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_cross

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
        negative_polyhedron_main_beam = self._create_polyhedron(plane_a0, lines, self.cut_plane_bias)
        negative_polyhedron_cross_beam = self._create_polyhedron(plane_b0, lines, self.cut_plane_bias)
        return negative_polyhedron_main_beam, negative_polyhedron_cross_beam
