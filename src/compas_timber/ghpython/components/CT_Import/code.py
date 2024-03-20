from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.data import json_load


class ExportTimberAssembly(component):

    def RunScript(self, filepath, import_):

        if not filepath:
            self.AddRuntimeMessage(Warning, "Input parameter Filepath failed to collect data")
        if not import_:
            return

        return json_load(filepath)
