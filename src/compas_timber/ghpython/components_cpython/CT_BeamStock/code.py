# r: compas_timber>=1.0.0
# flake8: noqa
import Grasshopper
import System
from ghpythonlib.treehelpers import tree_to_list

from compas_timber.planning import BeamStock
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class BeamStock(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, length, cross_section, spacing=0.0):
        if not item_input_valid_cpython(ghenv, length, "Length"):
            return
        if not item_input_valid_cpython(ghenv, cross_section, "CrossSection"):
            return

        # Convert inputs from tree to list
        cross_section = tree_to_list(cross_section)
        for cs in cross_section:
            if len(cs) != 2:
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    "CrossSection must be a tuple of two numeric values representing height and width.",
                )
                return

        # Duplicate data if necessary
        N = len(cross_section)

        n_length = list(length)
        if len(n_length) != N:
            for _ in range(N - len(n_length)):
                n_length.append(n_length[-1])

        n_spacing = list(spacing)
        if len(n_spacing) != N:
            for _ in range(N - len(n_spacing)):
                n_spacing.append(n_spacing[-1])

        # Create Stock objects
        stocks = []
        for l, cs, s in zip(length, cross_section, spacing):
            stock = BeamStock(l, cs, spacing=s)
            stocks.append(stock)

        return stocks
