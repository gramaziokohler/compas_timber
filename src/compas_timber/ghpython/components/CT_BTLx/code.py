from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Rhino
from compas_timber.assembly import TimberAssembly
from compas_timber.fabrication import BTLx
import compas.data

class WriteBTLx(component):
    def RunScript(self, Assembly, Path, Write):

        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return

        btlx = BTLx(Assembly)
        btlx.history["FileName"] = Rhino.RhinoDoc.ActiveDoc.Name

        if Write:
            if not Path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            with open(Path, "w") as f:
                f.write(str(btlx))

        return str(btlx)
