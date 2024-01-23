from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LButtJoint
from compas_timber.ghpython import JointOptions


class LButtJointOptions(component):
    def RunScript(self, gap, small_beam_butts):
        args = {}
        if gap:
            args["gap"] = gap
        if small_beam_butts:
            args["small_beam_butts"] = small_beam_butts
        options = JointOptions(LButtJoint, **args)

        return options
