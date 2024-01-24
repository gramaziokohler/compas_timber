from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LButtJoint
from compas_timber.ghpython import JointOptions


class LButtJointOptions(component):
    def RunScript(self, Gap, SmallBeamButts):
        args = {"gap": Gap, "small_beam_butts": SmallBeamButts}
        options = JointOptions(LButtJoint, **args)

        return options
