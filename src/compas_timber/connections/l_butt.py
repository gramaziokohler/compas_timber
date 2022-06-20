from pprint import pprint
from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from compas_timber.connections.joint import Joint
from compas_timber.utils.helpers import are_objects_identical
from compas_timber.utils.helpers import close

# TODO: replace direct references to beam objects


class LButtJoint(Joint):
    def __init__(self, main_beam, cross_beam, assembly):
        super(LButtJoint, self).__init__([main_beam, cross_beam], assembly)

        self.main_beam_key = main_beam.key
        self.cross_beam_key = cross_beam.key
        self.gap = 0.0  # float, additional gap, e.g. for glue

    def __eq__(self, other):
        tol = self.assembly.tol
        return (
            isinstance(other, LButtJoint) and
            super(LButtJoint, self).__eq__(other) and
            self.main_beam_key == other.main_beam_key and
            self.cross_beam_key == other.cross_beam_key and
            close(self.gap, other.gap, tol)
        )

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "gap": self.gap,
        }
        data_dict.update(super(LButtJoint, self).data)
        return data_dict

    @data.setter
    def data(self, value):
        # TODO: why can't I call the data.setter of Joint
        self.assembly = value["assembly"]
        self.key = value["key"]
        self.frame = value["frame"]

        self.main_beam_key = value["main_beam_key"]
        self.cross_beam_key = value["cross_beam_key"]
        self.gap = value["gap"]

    @property
    def joint_type(self):
        return 'L-Butt'

    @property
    def main_beam(self):
        return self.assembly.find_by_key(self.main_beam_key)

    @property
    def cross_beam(self):
        return self.assembly.find_by_key(self.cross_beam_key)

    def add_feature(self):
        pass


if __name__ == "__main__":

    pass
