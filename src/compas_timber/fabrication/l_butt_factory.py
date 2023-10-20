import math
from collections import OrderedDict
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.utils.compas_extra import intersection_line_plane
from compas_timber.connections import LButtJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxJackCut



class LButtFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(cls, joint):
        main_part = joint.parts[str(joint.joint.main_beam.key)]
        cross_part = joint.parts[str(joint.joint.cross_beam.key)]
        BTLxJackCut.apply_processes(joint.joint.cutting_plane_main, main_part, joint)
        BTLxJackCut.apply_processes(joint.joint.cutting_plane_cross, cross_part, joint)


BTLxJoint.register_joint(LButtJoint, LButtFactory)
