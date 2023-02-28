from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class ShowAssembly(component):
    def RunScript(self, Assembly):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return

        return Assembly.beams
