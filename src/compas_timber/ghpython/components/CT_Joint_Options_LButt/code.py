from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LButtJoint
from compas_timber.ghpython import JointOptions


class LButtJointOptions(component):
    def RunScript(self, small_beam_butts, modify_cross, reject_i):
        args = {}
        if small_beam_butts is not None:
            args["small_beam_butts"] = small_beam_butts
        if modify_cross is not None:
            args["modify_cross"] = modify_cross
        if reject_i is not None:
            args["reject_i"] = reject_i

        options = JointOptions(LButtJoint, **args)

        return options
