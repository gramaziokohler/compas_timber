from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.ghpython import JointOptions


class FrenchRidgeLapOptions(component):
    def RunScript(self, Cutoff):
        args = {}
        if Cutoff:
            args["cutoff"] = Cutoff
        options = JointOptions(FrenchRidgeLapJoint, **args)

        return options
