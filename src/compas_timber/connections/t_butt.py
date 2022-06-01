from pprint import pprint
from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from compas_timber.connections.joint import Joint
from compas_timber.utils.helpers import are_objects_identical
from compas.geometry import close

# TODO: replace direct references to beam objects


class TButtJoint(Joint):
    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
        super(TButtJoint, self).__init__(assembly, [main_beam, cross_beam])
        self.assembly = assembly  # TODO: needed?
        self.main_beam_key = None
        self.cross_beam_key = None
        self.gap = None  # float, additional gap, e.g. for glue

        if main_beam:
            self.main_beam_key = main_beam.key
        if cross_beam:
            self.cross_beam_key = cross_beam.key

    def __eq__(self, other):
        tol = self.assembly.tol
        return (
            isinstance(other, TButtJoint) and
            super(TButtJoint, self).__eq__(other) and
            self.main_beam_key == other.main_beam_key and
            self.cross_beam_key == other.cross_beam_key and
            close(self.gap, other.gap, tol)
        )

    @property
    def joint_type(self):
        return 'T-Butt'

    def is_identical(self, other_joint, additional_attributes=[]):
        attributes_to_compare = ['cross_beam', 'main_beam', 'gap', 'assembly'] + additional_attributes
        return are_objects_identical(self, other_joint, attributes_to_compare)

    @property
    def main_beam(self):
        try:
            return self.assembly.find_by_key(self.main_beam_key)
        except:
            return None

    @property
    def cross_beam(self):
        try:
            return self.assembly.find_by_key(self.cross_beam_key)
        except:
            return None

    @property
    def __find_side(self):
        """
        calculate which side of the cross beam is the cutting side for the main beam
        """

        # find the orientation of the mainbeam's centreline so that it's pointing outward of the joint
        #   find the closest end
        pm, pc = intersection_line_line(self.main_beam.centreline, self.cross_beam.centreline)
        p1 = self.main_beam.centreline.start
        p2 = self.main_beam.centreline.end
        d1 = distance_point_point(pm, p1)
        d2 = distance_point_point(pm, p2)

        if d1 < d2:
            centreline_vec = Vector.from_start_end(p1, p2)
        else:
            centreline_vec = Vector.from_start_end(p2, p1)

        # compare with side normals
        angles = [angle_vectors(self.cross_beam.side_frame(i).normal, centreline_vec) for i in range(4)]
        x = list(zip(angles, range(4)))
        x.sort()
        side = x[0][1]
        return side

    @property
    def cutting_plane(self):
        cfr = self.cross_beam.side_frame(self.__find_side)
        # TODO: move the frame's center to the intersection
        #cfr.point = Point(intersection_line_plane(self.main_beam.centreline, Plane.from_frame(cfr))[0], 1e-6)
        # TODO: flip normal
        return cfr

    def add_feature(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        # TODO: how to saveguard this being added multiple times?
        self.main_beam.add_feature(self.cutting_plane, 'trim')


if __name__ == "__main__":

    pass
