from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from ..connections.joint import Joint


class TLapJoint(Joint):
    def __init__(self, beamA, beamB, assembly):

        super(TLapJoint, self).__init__([beamA, beamB], assembly)

    @property
    def joint_type(self):
        return 'T-Lap'

    def add_feature(self):
        pass