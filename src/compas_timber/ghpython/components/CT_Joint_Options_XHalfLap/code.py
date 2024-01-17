from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import XHalfLapJoint
from compas_timber.connections.joint import JointOptions

class MyComponent(component):

    def RunScript(self, cut_plane_choice, cut_plane_bias):


        args = {"cut_plane_choice": cut_plane_choice, "cut_plane_bias": cut_plane_bias}
        options = JointOptions(XHalfLapJoint, **args)

        return options
