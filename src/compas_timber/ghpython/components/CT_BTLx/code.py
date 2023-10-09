from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas.rpc.proxy import Proxy
from compas_timber.assembly import TimberAssembly
import compas.data
#from compas_timber.utils.btlx_utils import BTLx_Part
import compas.geometry.brep
from compas.artists import Artist
from compas.geometry import Line

btlx = Proxy("compas_timber.fabrication.btlx")

class WriteBTLx(component):
    def RunScript(self, Assembly, Path, Write):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return

        btlx_json = compas.json_dumps(Assembly)
        strings = btlx.get_btlx_string(btlx_json)
        BTLx, blanks_data, msg = strings[0], strings[1], strings[2]

        print(msg)

        Blanks = []
        for blank in blanks_data:
            Blanks.append(blank.from_data)

        if Write:
            if not Path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            with open(Path, "w") as f:
                f.write(BTLx)


        return BTLx, Blanks
