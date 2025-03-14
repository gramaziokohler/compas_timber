import warnings

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane

from compas_timber.errors import BeamJoiningError

from .joint import Joint
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class LapJoint(Joint):
    """Abstract Lap type joint with functions common to L-Lap, T-Lap, and X-Lap Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    elements : list of :class:`~compas_timber.elements.Beam`
        The beams to be joined.
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
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

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(LapJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self.features = []

        self._main_ref_side_index = None
        self._cross_ref_side_index = None
        self._main_cutting_plane = None
        self._cross_cutting_plane = None

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    @property
    def main_ref_side_index(self):
        """The reference side index of the main beam."""
        if self._main_ref_side_index is None:
            self._main_ref_side_index = self._get_beam_ref_side_index(self.main_beam, self.cross_beam, self.flip_lap_side)
        return self._main_ref_side_index

    @property
    def cross_ref_side_index(self):
        """The reference side index of the cross beam."""
        if self._cross_ref_side_index is None:
            self._cross_ref_side_index = self._get_beam_ref_side_index(self.cross_beam, self.main_beam, self.flip_lap_side)
        return self._cross_ref_side_index

    @property
    def main_cutting_plane(self):
        """The face of the cross beam that cuts the main beam as a plane."""
        if self._main_cutting_plane is None:
            self._main_cutting_plane = self._get_cutting_plane(self.cross_beam, self.main_beam)
        return self._main_cutting_plane

    @property
    def cross_cutting_plane(self):
        """The face of the main beam that cuts the cross beam as a plane."""
        if self._cross_cutting_plane is None:
            self._cross_cutting_plane = self._get_cutting_plane(self.main_beam, self.cross_beam)
        return self._cross_cutting_plane

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

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint.

        Raises
        ------
        UserWarning
            If the elements are not compatible for the creation of the joint.
        """
        # TODO: This warning should be providing more information to the caller in regards to the affected beams and joints.
        if not are_beams_aligned_with_cross_vector(*self.elements):
            warnings.warn("The beams are not coplanar, therefore BTLxProcessings will not be generated for this joint", UserWarning)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)

    def _get_lap_lengths(self):
        lap_length_main = self.cross_beam.side_as_surface(self.cross_ref_side_index).ysize
        lap_length_cross = self.main_beam.side_as_surface(self.main_ref_side_index).ysize
        return lap_length_main, lap_length_cross

    def _get_lap_depths(self):
        """Returns the lap depths from the distance between the two lap faces and the bias value."""
        main_frame = self.main_beam.ref_sides[self.main_ref_side_index]
        cross_frame = self.cross_beam.ref_sides[self.cross_ref_side_index]

        vect = main_frame.point - cross_frame.point
        cross_vect = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
        cross_vect.unitize()
        lap_depth = abs(cross_vect.dot(vect))

        main_lap_depth = lap_depth * self.cut_plane_bias
        cross_lap_depth = lap_depth * (1 - self.cut_plane_bias)

        main_height = self.main_beam.get_dimensions_relative_to_side(self.main_ref_side_index)[1]
        cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_ref_side_index)[1]

        if main_lap_depth >= main_height or cross_lap_depth >= cross_height:  # TODO: should we instead bypass the bias and use the max. possible depth?
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Lap depth is bigger than the beam's height. Consider revising the bias.")
        return main_lap_depth, cross_lap_depth

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
