import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLx


class WriteBTLx(component):
    def RunScript(self, model, path, write):
        if not model:
            self.AddRuntimeMessage(Warning, "Input parameter Model failed to collect data")
            return

        btlx = BTLx(model)
        btlx.history["FileName"] = Rhino.RhinoDoc.ActiveDoc.Name

        if write:
            if not path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            with open(path, "w") as f:
                f.write(btlx.btlx_string())
        return btlx.btlx_string()
