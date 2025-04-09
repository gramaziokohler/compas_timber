# flake8: noqa
import Grasshopper

from compas.scene import SceneObject


class ShowJoiningErrors(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, debug_info, i: int):
        if i is None:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'i' failed to collect data")
            i = 0
        if not debug_info:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'DebugInfo' failed to collect data")
            return
        if not debug_info.joint_errors:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "No joining errors found in input parameter 'DebugInfo'")
            return
        joining_errors = debug_info.joint_errors
        i = int(i) % len(joining_errors)
        error = joining_errors[i]

        geometries = [beam.blank for beam in error.beams]
        geometries.extend(error.debug_geometries)
        geo_objs = [SceneObject(item=geo) for geo in geometries]
        output = []
        for obj in geo_objs:
            output.extend(obj.draw())

        return error.debug_info, output
