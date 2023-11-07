from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxJackCut


class TButtFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(cls, joint, parts):
        part = parts[str(joint.main_beam.key)]
        cut_plane = joint.cutting_plane
        BTLxJackCut.apply_process(part, cut_plane, "T-Butt Joint")


BTLxJoint.register_joint(TButtJoint, TButtFactory)
