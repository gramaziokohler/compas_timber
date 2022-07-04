from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane

from ..connections.joint import Joint


class TLapJoint(Joint):
    def __init__(self, assembly, beamA, beamB):

        super(TLapJoint, self).__init__(assembly, [beamA, beamB])

    @property
    def joint_type(self):
        return "T-Lap"

    def add_feature(self):
        pass
