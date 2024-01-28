# flake8: noqa
from compas.scene import SceneObject

from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from ghpythonlib.componentbase import executingcomponent as component


class ShowJoiningErrors(component):
    def RunScript(self, debug_info, index):
        if index is None:
            self.AddRuntimeMessage(Warning, "Input parameter 'i' failed to collect data")
            return
        if not debug_info:
            self.AddRuntimeMessage(Warning, "Input parameter 'DebugInfo' failed to collect data")
            return
        if not debug_info.joining_errors:
            self.AddRuntimeMessage(Warning, "No joining errors found in input parameter 'DebugInfo'")
            return
        joining_errors = debug_info.joining_errors
        index = int(index) % len(joining_errors)
        error = joining_errors[index]

        self.AddRuntimeMessage(Warning, error.debug_info)

        geometries = [beam.blank for beam in error.beams]
        geo_objs = [SceneObject(geo) for geo in geometries]
        output = []
        for obj in geo_objs:
            output.extend(obj.draw())

        return output
