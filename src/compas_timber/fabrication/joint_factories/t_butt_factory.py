from compas_timber.fabrication import BTLx
from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLxJackCut


class TButtFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        part = parts[str(joint.main_beam.key)]
        cut_plane = joint.cutting_plane
        part.processings.append(BTLxJackCut.create_process(part, cut_plane, "T-Butt Joint"))


BTLx.register_joint(TButtJoint, TButtFactory)
