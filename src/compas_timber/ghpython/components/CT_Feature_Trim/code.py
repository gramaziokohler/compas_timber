from compas_rhino.conversions import plane_to_compas_frame
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import FeatureDefinition
from compas_timber.elements import CutFeature


class TrimmingFeature(component):
    def RunScript(self, beam, plane):
        if not plane:
            self.AddRuntimeMessage(Warning, "Input parameter Plane failed to collect data")

        if not isinstance(beam, list):
            beam = [beam]

        feature = CutFeature(plane_to_compas_frame(plane))
        return FeatureDefinition(feature, beam)
