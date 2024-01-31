from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import THalfLapJoint
from compas_timber.ghpython import JointOptions


class THalfLapJointOptions(component):
    def RunScript(self, flip_lap_side, cut_plane_bias):
        args = {}
        if flip_lap_side:
            args["flip_lap_side"] = flip_lap_side
        if cut_plane_bias:
            args["cut_plane_bias"] = cut_plane_bias
        options = JointOptions(THalfLapJoint, **args)

        return options
