from compas_timber.fabrication import BTLx
from compas_timber.connections import LButtJoint
from compas_timber.fabrication import BTLxJackCut


class LButtFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        main_part = parts[str(joint.main_beam.key)]
        cross_part = parts[str(joint.cross_beam.key)]
        main_part.processings.append(BTLxJackCut.create_process(main_part, joint.cutting_plane_main, "L-Butt Joint"))
        cross_part.processings.append(BTLxJackCut.create_process(cross_part, joint.cutting_plane_cross, "L-Butt Joint"))


BTLx.register_joint(LButtJoint, LButtFactory)
