from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas.rpc.proxy import Proxy
from compas_timber.assembly import TimberAssembly
import compas.data

btlx = Proxy("compas_timber.utils.btlx")


class WriteBTLx(component):
    def RunScript(self, Assembly, Path, Write):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return

        btlx_json = compas.json_dumps(Assembly.data)

        BTLx = btlx.get_btlx_string(btlx_json)
        if Write:
            if not Path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            with open(Path, "w") as f:
                f.write(BTLx)

        return BTLx
