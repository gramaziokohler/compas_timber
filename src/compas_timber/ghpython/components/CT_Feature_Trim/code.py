from compas_rhino.conversions import plane_to_compas_frame
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import CutFeature


class TrimmingFeature(component):
    def RunScript(self, beam, plane):
        if not beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beam failed to collect data")
        if not plane:
            self.AddRuntimeMessage(Warning, "Input parameter Plane failed to collect data")
        if not (beam and plane):
            return

        if not isinstance(beam, list):
            beam = [beam]

        feature = CutFeature(plane_to_compas_frame(plane))
        return FeatureDefinition(feature, beam)
