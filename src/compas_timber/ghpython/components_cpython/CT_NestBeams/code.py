# r: compas_timber>=1.0.0
# flake8: noqa
import Grasshopper
import System

from compas_timber.planning import BeamNester as CTBeamNester
from compas_timber.planning import BeamStock
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class BeamNester(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model, stock_catalog, spacing, fast):
        if not item_input_valid_cpython(ghenv, model, "Model"):
            return
        if not item_input_valid_cpython(ghenv, stock_catalog, "Stock Catalog"):
            return

        # Validate stock catalog items
        stock_catalog = list(stock_catalog)
        for stock in stock_catalog:
            if not isinstance(stock, BeamStock):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    f"All items in Stock Catalog must be of type Stock. Found {type(stock)}",
                )
                return

        fast = fast or False
        beam_nester = CTBeamNester(model, stock_catalog, spacing=spacing)
        nesting_result = beam_nester.nest(fast=fast)
        return nesting_result
