from compas_rhino.conversions import line_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


from compas_timber.fabrication import DeferredDrilling


class DrillHoleFeature(component):
    def RunScript(self, element, line, diameter):
        if not element:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not line:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")
        if not diameter:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")

        if not (element and line and diameter):
            return

        if not isinstance(element, list):
            element = [element]

        return DeferredDrilling.from_shapes(line_to_compas(line), element, diameter=diameter)
