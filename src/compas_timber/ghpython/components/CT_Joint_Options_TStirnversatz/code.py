from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import TStirnversatzJoint
from compas_timber.ghpython import JointOptions


class TStirnversatzJointOptions(component):
    def RunScript(self, Gap, CutDepth, ExtendCut):
        args = {}
        if Gap:
            args["gap"] = Gap
        if 0.05 < CutDepth < 0.9 and CutDepth is not None:
            args["cut_depth"] = CutDepth
        if ExtendCut is not None:
            args["extend_cut"] = ExtendCut
        options = JointOptions(TStirnversatzJoint, **args)

        return options
