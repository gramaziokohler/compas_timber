from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas.rpc.proxy import Proxy

btlx = Proxy("compas_timber.utils.btlx")


class WriteBTLx(component):
    def RunScript(self, Assembly, Path, Write):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return
        if not Path:
            self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
            return

        BTLx = btlx.get_btlx_string(Assembly)
        if Write:
            with open(Path, "w") as f:
                f.write(BTLx)

        return BTLx
