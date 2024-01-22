from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import XHalfLapJoint
from compas_timber.ghpython import JointOptions


class XHalfLapJointOptions(component):
    def RunScript(self, FlipLap, cut_plane_bias):
        bias = cut_plane_bias or 0.5
        args = {"flip_lap_side": FlipLap, "cut_plane_bias": bias}
        options = JointOptions(XHalfLapJoint, **args)

        return options
