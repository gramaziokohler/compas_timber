# flake8: noqa
import Grasshopper

from compas.scene import SceneObject



class ShowFeatureErrors(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, debug_info, i: int):
        if i is None:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'i' failed to collect data")
            i = 0
        if not debug_info:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'DebugInfo' failed to collect data")
            return
        if not debug_info.feature_errors:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "No feature errors found in input parameter 'DebugInfo'")
            return
        feature_errors = debug_info.feature_errors
        i = int(i) % len(feature_errors)
        error = feature_errors[i]

        geometries = [error.feature_geometry, error.element_geometry]
        geometries = flatten(geometries)
        geo_objs = [SceneObject(item=geo) for geo in geometries]
        output = []
        for obj in geo_objs:
            output.extend(obj.draw())

        return error.message, output


def flatten(lst):
    if not lst:
        return lst
    if isinstance(lst[0], list):
        return flatten(lst[0]) + flatten(lst[1:])
    return lst[:1] + flatten(lst[1:])
