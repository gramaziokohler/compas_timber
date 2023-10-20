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
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxProcess
from compas_timber.fabrication import BTLxJackCut



class LMiterFactory(object):
    def __init__(self):
        pass
    @classmethod
    def apply_processes(cls, joint):
        BTLxJackCut.apply_processes(joint.joint.cutting_planes[0], joint.parts.values()[0], joint)
        BTLxJackCut.apply_processes(joint.joint.cutting_planes[1], joint.parts.values()[1], joint)


BTLxJoint.register_joint(LMiterJoint, LMiterFactory)
