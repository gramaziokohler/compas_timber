from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import XHalfLapJoint
from compas_timber.connections.joint import JointOptions


class MyComponent(component):
    def RunScript(self, cut_plane_choice, cut_plane_bias):
        bias = cut_plane_bias or 0.5
        args = {"cut_plane_choice": cut_plane_choice, "cut_plane_bias": bias}
        options = JointOptions(XHalfLapJoint, **args)

        return options
