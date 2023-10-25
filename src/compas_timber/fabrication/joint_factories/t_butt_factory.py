from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxJackCut


class TButtFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(cls, btlx_joint):
        part = btlx_joint.parts[str(btlx_joint.joint.main_beam.key)]
        cut_plane = btlx_joint.joint.cutting_plane
        BTLxJackCut.apply_process(part, cut_plane, btlx_joint)


BTLxJoint.register_joint(TButtJoint, TButtFactory)
