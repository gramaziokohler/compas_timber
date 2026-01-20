from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import intersection_line_line

from compas_timber.connections.joint import Joint
from compas_timber.connections.lap_joint import LapJoint
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements import Beam
from compas_timber.fabrication import FrenchRidgeLap
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication.jack_cut import JackRafterCut


class YSpatialLapJoint(Joint):
    def __init__(self, cross_beam: Beam, *main_beams: Beam, **kwargs):
        super().__init__(**kwargs)
        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.mill_depth_a = 2
        self.mill_depth_b = 4
        self._plane_a = None
        self._plane_b = None
        self._plane_a_lap = None
        self._plane_b_lap = None

    @property
    def __data__(self):
        raise NotImplementedError

    @property
    def beams(self):
        return [self.cross_beam] + self.main_beams

    @property
    def elements(self):
        return self.beams

    @property
    def beam_a(self):
        return self.main_beams[0]

    @property
    def beam_b(self):
        return self.main_beams[1]

    @property
    def plane_a(self):
        if not self._plane_a:
            ref_side_index = (self.ref_side_index(self.beam_a, self.beam_b) + 2) % 4
            plane_a = Plane.from_frame(self.beam_a.ref_sides[ref_side_index])
            plane_a.point += self.mill_depth_a * -plane_a.normal
            self._plane_a = plane_a
        return self._plane_a

    @property
    def plane_b(self):
        if not self._plane_b:
            ref_side_index = (self.ref_side_index(self.beam_b, self.beam_a) + 2) % 4
            plane_b = Plane.from_frame(self.beam_b.ref_sides[ref_side_index])
            plane_b.point += self.mill_depth_b * -plane_b.normal
            self._plane_b = plane_b
        return self._plane_b

    @property
    def plane_a_lap(self):
        if not self._plane_a_lap:
            ref_side_index = self.ref_side_index(self.cross_beam, self.beam_a)
            plane_a_lap = Plane.from_frame(self.cross_beam.ref_sides[ref_side_index])
            self._plane_a_lap = plane_a_lap
        return self._plane_a_lap

    @property
    def plane_b_lap(self):
        if not self._plane_b_lap:
            ref_side_index = (self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4
            plane_b_lap = Plane.from_frame(self.cross_beam.ref_sides[ref_side_index])
            plane_b_lap.normal *= -1
            self._plane_b_lap = plane_b_lap
        return self._plane_b_lap

    @property
    def main_beams_plane(self):
        intersection_point = intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)
        point = Point(*intersection_point[0])
        plane = Plane.from_point_and_two_vectors(point, self.main_beams[0].centerline.direction, self.main_beams[1].centerline.direction)
        return plane

    def cross_beam_ref_side_inde(self, beam):
        raise NotImplementedError

    def main_beam_ref_side_index(self, beam):
        raise NotImplementedError

    def ref_side_index(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """
        Calculates and adds the necessary extensions to the beams.
        """
        self._extend_cross_beam()
        self._extend_main_beam(self.main_beams[0], self.main_beams[1])
        self._extend_main_beam(self.main_beams[1], self.main_beams[0])
        # Extend the cross beam, to the plane created by the two main_beam

    def _extend_cross_beam(self):
        intersection_point = intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)
        max_main_beams_height = max([beam.get_dimensions_relative_to_side(self.ref_side_index(beam, self.cross_beam))[1] for beam in self.main_beams])
        cross_beam_direction = self.cross_beam.centerline.direction
        if self.cross_beam.centerline.point.distance_to_point(Point(*intersection_point[0])) < self.cross_beam.centerline.end.distance_to_point(Point(*intersection_point[0])):
            cross_beam_direction = cross_beam_direction.scaled(-1)
        plane = self.main_beams_plane
        plane.point += max_main_beams_height / 2 * cross_beam_direction
        blank = self.cross_beam.extension_to_plane(plane)
        self.cross_beam.add_blank_extension(*blank)

    def _extend_main_beam(self, beam, other_beam):
        plane_ref_side_index = (self.ref_side_index(other_beam, beam) + 2) % 4
        plane = Plane.from_frame(other_beam.ref_sides[plane_ref_side_index])
        blank = beam.extension_to_plane(plane)
        beam.add_blank_extension(*blank)
        return beam

    def add_features(self):
        # Apply the lap_feature to the beam_a
        ref_side_index = self.ref_side_index(self.cross_beam, self.beam_a)
        plane_a_lap = Plane.from_frame(self.cross_beam.ref_sides[ref_side_index])
        length = self.cross_beam.get_dimensions_relative_to_side(ref_side_index)[1]
        lap_a = Lap.from_plane_and_beam(plane_a_lap, self.beam_a, length=length, depth=5, ref_side_index=1)
        jack_plane = self.cross_beam.ref_sides[(ref_side_index + 2) % 4]
        jackrc_a = JackRafterCut.from_plane_and_beam(jack_plane, self.beam_a)
        self.beam_a.add_feature(lap_a)
        self.beam_a.add_feature(jackrc_a)

    def restore_beams_from_keys(self, model):
        raise NotImplementedError

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        raise NotImplementedError
