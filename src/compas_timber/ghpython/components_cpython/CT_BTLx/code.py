# r: compas_timber>=1.0.1
# flake8: noqa
import Grasshopper
import Rhino

from compas_timber.fabrication import BTLxWriter
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class WriteBTLx(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model, nesting_result, path, write: bool):
        if not item_input_valid_cpython(ghenv, model, "Model"):
            return

        btlx = BTLxWriter(file_name=str(Rhino.RhinoDoc.ActiveDoc.Name))

        if write:
            if not item_input_valid_cpython(ghenv, path, "Path"):
                return
            XML = btlx.write(model, path, nesting_result=nesting_result)
        else:
            XML = btlx.model_to_xml(model, nesting_result=nesting_result)

        return XML
