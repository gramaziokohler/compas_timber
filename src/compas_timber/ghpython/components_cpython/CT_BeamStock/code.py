# r: compas_timber>=1.0.0
# flake8: noqa
import Grasshopper
import System
from ghpythonlib.treehelpers import tree_to_list

from compas_timber.planning import BeamStock as CTBeamStock
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class BeamStock(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, length: System.Collections.Generic.List[float], cross_section: Grasshopper.DataTree[float]):
        if not item_input_valid_cpython(ghenv, length, "Length"):
            return
        if not item_input_valid_cpython(ghenv, cross_section, "CrossSection"):
            return

        # Convert inputs from tree to list
        length = list(length)
        cross_section = tree_to_list(cross_section)

        # If user passes a flat list, nest it
        if all(isinstance(x, float) for x in cross_section):
            cross_section = [cross_section]

        for cs in cross_section:
            if len(cs) != 2:
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    "CrossSection must be a tuple of two numeric values representing height and width.",
                )
                return

        # Duplicate data if necessary
        N = len(cross_section)
        if len(length) != N:
            for _ in range(N - len(length)):
                length.append(length[0])

        # Create Stock objects
        stocks = []
        for l, cs in zip(length, cross_section):
            stock = CTBeamStock(length=l, cross_section=cs)
            stocks.append(stock)

        return stocks
