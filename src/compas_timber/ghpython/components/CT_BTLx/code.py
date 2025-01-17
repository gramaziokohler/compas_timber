import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLxWriter


class WriteBTLx(component):
    def RunScript(self, model, path, write):
        if not model:
            self.AddRuntimeMessage(Warning, "Input parameter Model failed to collect data")
            return

        btlx = BTLxWriter(file_name=str(Rhino.RhinoDoc.ActiveDoc.Name))

        if write:
            if not path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            XML = btlx.write(model, path)
        else:
            XML = btlx.model_to_xml(model)

        return XML
