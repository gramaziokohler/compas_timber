# flake8: noqa
import Grasshopper
import Rhino

from compas_timber.fabrication import BTLxWriter


class WriteBTLx(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model, path, write: bool):
        if not model:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter Model failed to collect data")
            return

        btlx = BTLxWriter(file_name=str(Rhino.RhinoDoc.ActiveDoc.Name))

        if write:
            if not path:
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter Path failed to collect data")
                return
            XML = btlx.write(model, path)
        else:
            XML = btlx.model_to_xml(model)

        return XML
