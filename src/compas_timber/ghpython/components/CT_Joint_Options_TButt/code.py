from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import TButtJoint
from compas_timber.ghpython import JointOptions


class TButtJointOptions(component):
    def RunScript(self, Gap):

        args = {}
        if Gap:
            args["gap"] = Gap
        options = JointOptions(TButtJoint, **args)

        return options
