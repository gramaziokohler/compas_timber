import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLx


class WriteBTLx(component):
    def RunScript(self, Model, Path, write):
        if not Model:
            self.AddRuntimeMessage(Warning, "Input parameter Model failed to collect data")
            return

        btlx = BTLx(Model)
        btlx.history["FileName"] = Rhino.RhinoDoc.ActiveDoc.Name

        if write:
            if not Path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            if Path[-5:] != ".btlx":
                Path += ".btlx"
            with open(Path, "w") as f:
                f.write(btlx.btlx_string())
        BTLx = btlx.btlx_string()
        return BTLx
