from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas_timber.utils.btlx import BTLx

class WriteBTLx(component):
    def RunScript(self, Assembly, Path,  Write):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return
        if not Path:
            self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
            return

        btlx = BTLx(Assembly)
        if Write:
            btlx.writeBTLx(Path)
