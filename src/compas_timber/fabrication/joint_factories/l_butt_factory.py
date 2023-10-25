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
        BTLxJackCut.apply_process(main_part, joint.joint.cutting_plane_main, joint)
        BTLxJackCut.apply_process(cross_part, joint.joint.cutting_plane_cross, joint)


BTLxJoint.register_joint(LButtJoint, LButtFactory)
