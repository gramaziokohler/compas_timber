from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import TStirnversatzJoint
from compas_timber.ghpython import JointOptions


class TStirnversatzJointOptions(component):
    def RunScript(self, Gap):
        args = {}
        if Gap:
            args["gap"] = Gap
        options = JointOptions(TStirnversatzJoint, **args)

        return options
