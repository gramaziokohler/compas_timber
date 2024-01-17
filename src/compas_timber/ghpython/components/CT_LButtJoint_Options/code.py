from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LButtJoint
from compas_timber.connections.joint import JointOptions


class MyComponent(component):
    def RunScript(self, Gap, Small_Beam_Butts):
        args = {"gap": Gap, "smallBeamButts": Small_Beam_Butts}
        options = JointOptions(LButtJoint, **args)

        return options
