import math
from collections import OrderedDict
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxProcess
from compas_timber.fabrication import BTLxFrenchRidgeLap
from compas_timber.fabrication import BTLxJackCut


class FrenchRidgeFactory(object):
    def __init__(self, joint):
        pass

    @classmethod
    def apply_processes(self, joint):
        top_beam_key = joint.parts.keys()[0]
        BTLxFrenchRidgeLap.apply_processes(joint, top_beam_key)


BTLxJoint.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
