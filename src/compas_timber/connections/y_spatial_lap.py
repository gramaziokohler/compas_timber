from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import intersection_line_line

from compas_timber.connections.elements import Beam
from compas_timber.connections.joint import Joint
from compas_timber.connections.utilities import beam_ref_side_incidence


class YSpatialLapJoint(Joint):
    def __init__(self, cross_beam: Beam, *main_beams: Beam, **kwargs):
        super().__init__(**kwargs)
        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)

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
    def main_beams_plane(self):
        intersection_point = intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)
        point = Point(*intersction_point[0])
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
        # Extend the cross beam, to the plane created by the two main_beam

    def add_features(self):
        raise NotImplementedError

    def restore_beams_from_keys(self, model):
        raise NotImplementedError

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        raise NotImplementedError
