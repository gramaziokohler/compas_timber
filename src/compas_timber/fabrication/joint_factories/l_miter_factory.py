from compas_timber.fabrication import BTLx
from compas_timber.connections import LMiterJoint
from compas_timber.fabrication import BTLxJackCut


class LMiterFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        parts[str(joint.beams[0].key)].processings.append(
            BTLxJackCut.create_process(parts[str(joint.beams[0].key)], joint.cutting_planes[0], "L-Miter Joint")
        )
        parts[str(joint.beams[1].key)].processings.append(
            BTLxJackCut.create_process(parts[str(joint.beams[1].key)], joint.cutting_planes[1], "L-Miter Joint")
        )


BTLx.register_joint(LMiterJoint, LMiterFactory)
