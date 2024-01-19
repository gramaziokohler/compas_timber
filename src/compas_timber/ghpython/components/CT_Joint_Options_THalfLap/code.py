from ghpythonlib.componentbase import executingcomponent as component


from compas_timber.connections import THalfLapJoint
from compas_timber.connections.joint import JointOptions

class MyComponent(component):

    def RunScript(self, flip_lap_side, cut_plane_bias):
        bias = cut_plane_bias or 0.5
        args = {"flip_lap_side": flip_lap_side, "cut_plane_bias": bias}
        options = JointOptions(THalfLapJoint, **args)

        return options
