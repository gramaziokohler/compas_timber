from compas_rhino.conversions import plane_to_compas_frame
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import BeamTrimmingFeature


class TrimmingFeature(component):
    def RunScript(self, beams, planes):
        if not beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beam failed to collect data")
        if not planes:
            self.AddRuntimeMessage(Warning, "Input parameter Pln failed to collect data")
        if not (beams and planes):
            return

        if not isinstance(beams, list):
            beams = [beams]
        if not isinstance(planes, list):
            planes = [planes]

        feautre_defs = []
        for plane in planes:
            feature = BeamTrimmingFeature(plane_to_compas_frame(plane))
            feautre_defs.append(FeatureDefinition(feature, beams))

        return feautre_defs
