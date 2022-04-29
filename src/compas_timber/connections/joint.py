from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data

# TODO: replace direct references to beam objects


class Joint(Data):
    def __init__(self, assembly=None, beamA=None, beamB=None):
        super(Joint, self).__init__()
        self.assembly = assembly
        self.beamA_key = beamA.key
        self.beamB_key = beamB.key
        self.joint_type_name = ''
        self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint

        assembly.add_joint(self)
        assembly.connect(self, [beamA, beamB])

    @property
    def beams(self):
        return [self.beamA, self.beamB]

    @property
    def beamA(self):
        return self.assembly.find_by_key(self.beamA_key)

    @property
    def beamB(self):
        return self.assembly.find_by_key(self.beamB_key)
