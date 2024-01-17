from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LMiterJoint
from compas_timber.connections.joint import JointOptions


class MyComponent(component):
    def RunScript(self, Cutoff):
        args = {"cutoff": Cutoff}
        options = JointOptions(LMiterJoint, **args)

        return options
