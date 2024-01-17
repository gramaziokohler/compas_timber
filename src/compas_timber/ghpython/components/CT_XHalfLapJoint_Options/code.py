from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning



from compas_timber.connections import TButtJoint
from compas_timber.connections.joint import JointOptions

class MyComponent(component):

    def RunScript(self, Gap):


        args = {"gap": Gap}
        options = JointOptions(TButtJoint, **args)

        return options

