from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from ..connections.joint import Joint


class TLapJoint(Joint):
    def __init__(self, assembly=None, beamA=None, beamB=None):

        super(TLapJoint, self).__init__(assembly, [beamA, beamB])
        self.assembly = assembly
        #self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint

    @property
    def joint_type(self):
        return 'T-Lap'

    def apply_feature(self):
        pass