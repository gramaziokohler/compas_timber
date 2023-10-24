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
    def __init__(self):
        pass

    @classmethod
    def apply_processes(self, joint):
        top_key, top_part = joint.parts.items()[0]
        top_end = joint.ends[top_key]
        top_part._test.append(
            top_part.reference_surfaces[str(joint.joint.reference_face_indices[str(top_part.beam.key)])]
        )
        BTLxFrenchRidgeLap.apply_processes(top_part, joint, True, top_end)

        bottom_key, bottom_part = joint.parts.items()[1]
        bottom_end = joint.ends[bottom_key]
        bottom_part._test.append(
            bottom_part.reference_surfaces[str(joint.joint.reference_face_indices[str(bottom_part.beam.key)])]
        )
        BTLxFrenchRidgeLap.apply_processes(bottom_part, joint, False, bottom_end)


BTLxJoint.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
