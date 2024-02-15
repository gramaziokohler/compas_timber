from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import NullJoint
from compas_timber.ghpython import JointOptions


class NullJointComponent(component):
    def RunScript(self):
        options = JointOptions(NullJoint, ["first_beam", "second_beam"], **{})
        return options
