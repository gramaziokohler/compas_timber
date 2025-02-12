from compas_rhino.conversions import plane_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import DeferredJackRafterCut



class TrimmingFeature(component):
    def RunScript(self, element, plane):
        if not plane:
            self.AddRuntimeMessage(Warning, "Input parameter Plane failed to collect data")

        if not isinstance(element, list):
            element = [element]

        return DeferredJackRafterCut(plane_to_compas(plane), element)
