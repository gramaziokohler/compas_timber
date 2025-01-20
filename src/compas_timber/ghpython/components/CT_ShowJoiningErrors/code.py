# flake8: noqa
from compas.scene import SceneObject
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class ShowJoiningErrors(component):
    def RunScript(self, debug_info, index):
        if index is None:
            self.AddRuntimeMessage(Warning, "Input parameter 'i' failed to collect data")
            index = 0
        if not debug_info:
            self.AddRuntimeMessage(Warning, "Input parameter 'DebugInfo' failed to collect data")
            return
        if not debug_info.joint_errors:
            self.AddRuntimeMessage(Warning, "No joining errors found in input parameter 'DebugInfo'")
            return
        joining_errors = debug_info.joint_errors
        index = int(index) % len(joining_errors)
        error = joining_errors[index]

        geometries = [beam.blank for beam in error.beams]
        geometries.extend(error.debug_geometries)
        geo_objs = [SceneObject(item=geo) for geo in geometries]
        output = []
        for obj in geo_objs:
            output.extend(obj.draw())

        return error.debug_info, output
