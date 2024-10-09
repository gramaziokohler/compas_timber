# flake8: noqa
from compas.scene import SceneObject
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class ShowFeatureErrors(component):
    def RunScript(self, debug_info, index):
        if index is None:
            self.AddRuntimeMessage(Warning, "Input parameter 'i' failed to collect data")
            return
        if not debug_info:
            self.AddRuntimeMessage(Warning, "Input parameter 'DebugInfo' failed to collect data")
            return
        if not debug_info.feature_errors:
            self.AddRuntimeMessage(Warning, "No feature errors found in input parameter 'DebugInfo'")
            return
        feature_errors = debug_info.feature_errors
        index = int(index) % len(feature_errors)
        error = feature_errors[index]

        geometries = [error.feature_geometry, error.element_geometry]
        geo_objs = [SceneObject(item=geo) for geo in geometries]
        output = []
        for obj in geo_objs:
            output.extend(obj.draw())

        return error.message, output
