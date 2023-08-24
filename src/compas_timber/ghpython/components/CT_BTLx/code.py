from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas_timber.utils.btlx import BTLx

class WriteBTLx(component):
    def RunScript(self, Assembly, Location, Name, Write):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return
        if not Location:
            self.AddRuntimeMessage(Warning, "Input parameter Location failed to collect data")
            return
        if not Name:
            self.AddRuntimeMessage(Warning, "Input parameter Name failed to collect data")
            return

        btlx = BTLx(Assembly)
        if Write:
            btlx.writeBTLx(Location, Name)
