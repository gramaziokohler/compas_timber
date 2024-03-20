from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.data import json_dump


class ExportTimberAssembly(component):

    def RunScript(self, assembly, filepath, export):

        if not assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
        if not filepath:
            self.AddRuntimeMessage(Warning, "Input parameter Filepath failed to collect data")
        if not export:
            return

        json_dump(assembly, filepath)
