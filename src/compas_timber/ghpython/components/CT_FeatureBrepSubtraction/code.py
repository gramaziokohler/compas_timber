from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.geometry import Brep

from compas_timber.parts import BeamBooleanSubtraction
from compas_timber.ghpython import FeatureDefinition


class BrepSubtractionFeature(component):
    def RunScript(self, beams, breps):
        if not beams:
            self.AddRuntimeMessage(Warning, "Input parameter beams failed to collect data")
        if not breps:
            self.AddRuntimeMessage(Warning, "Input parameter breps failed to collect data")
        if not (beams and breps):
            return

        if not isinstance(beams, list):
            beams = [beams]
        if not isinstance(breps, list):
            breps = [breps]

        feature_defs = []
        for brep in breps:
            feature = BeamBooleanSubtraction(Brep.from_native(brep))
            feature_defs.append(FeatureDefinition(feature, beams))

        return feature_defs
