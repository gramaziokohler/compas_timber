from compas.geometry import Brep
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import BeamBooleanSubtraction


class BrepSubtractionFeature(component):
    def RunScript(self, Beams, Breps):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Breps:
            self.AddRuntimeMessage(Warning, "Input parameter Breps failed to collect data")
        if not (Beams and Breps):
            return

        if not isinstance(Beams, list):
            Beams = [Beams]
        if not isinstance(Breps, list):
            Breps = [Breps]

        FeatureDefs = []
        for brep in Breps:
            feature = BeamBooleanSubtraction(Brep.from_native(brep))
            FeatureDefs.append(FeatureDefinition(feature, Beams))

        return FeatureDefs
