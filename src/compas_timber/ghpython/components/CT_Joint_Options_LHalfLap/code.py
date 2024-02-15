from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import LHalfLapJoint
from compas_timber.ghpython import JointOptions


class LHalfLapJointOptions(component):
    def RunScript(self, flip_lap_side, cut_plane_bias):
        args = {}
        if flip_lap_side:
            args["flip_lap_side"] = flip_lap_side
        if cut_plane_bias:
            args["cut_plane_bias"] = cut_plane_bias

        options = JointOptions(LHalfLapJoint, ["top_beam", "bottom_beam"],**args)

        return options
