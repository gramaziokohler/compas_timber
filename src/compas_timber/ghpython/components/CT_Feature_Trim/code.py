from compas_rhino.conversions import plane_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLxFromGeometryDefinition
from compas_timber.fabrication import JackRafterCut


class TrimmingFeature(component):
    def RunScript(self, beam, plane):
        if not plane:
            self.AddRuntimeMessage(Warning, "Input parameter Plane failed to collect data")

        if not isinstance(beam, list):
            beam = [beam]

        return BTLxFromGeometryDefinition(JackRafterCut, plane_to_compas(plane), beam)
