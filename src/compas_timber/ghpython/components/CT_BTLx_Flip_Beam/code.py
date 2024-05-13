import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLx


class WriteBTLx(component):
    def RunScript(self, btlx, path, write, beam_key, split_into_two):
        if not btlx:
            self.AddRuntimeMessage(Warning, "Input parameter btlx failed to collect data")
            return
        btlx.history["FileName"] = Rhino.RhinoDoc.ActiveDoc.Name

        if write:
            if not path:
                self.AddRuntimeMessage(Warning, "Input parameter Path failed to collect data")
                return
            path = path.split(".")[0] if "." in path else path
            path_end = "_" + str(beam_key) + "_SPLIT"  + ".btlx"
            path += path_end
            with open(path, "w") as f:
                f.write(btlx.get_split_strings(beam_key, split_into_two))
        return btlx.get_split_strings(beam_key, split_into_two)
