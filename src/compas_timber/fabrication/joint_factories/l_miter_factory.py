from compas_timber.connections import LMiterJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxJackCut


class LMiterFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(cls, joint):
        BTLxJackCut.apply_process(joint.parts.values()[0], joint.joint.cutting_planes[0], joint)
        BTLxJackCut.apply_process(joint.parts.values()[1], joint.joint.cutting_planes[1], joint)


BTLxJoint.register_joint(LMiterJoint, LMiterFactory)
