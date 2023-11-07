from compas_timber.connections import LMiterJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxJackCut


class LMiterFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(cls, joint, parts):
        parts.values()[0].processings.append(BTLxJackCut.create_process(parts.values()[0], joint.cutting_planes[0], "L-Miter Joint"))
        parts.values()[1].processings.append(BTLxJackCut.create_process(parts.values()[1], joint.cutting_planes[1], "L-Miter Joint"))


BTLxJoint.register_joint(LMiterJoint, LMiterFactory)
