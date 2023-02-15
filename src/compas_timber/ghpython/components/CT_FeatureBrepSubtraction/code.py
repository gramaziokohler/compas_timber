from compas.geometry import Brep
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import BeamBooleanSubtraction


class BrepSubtractionFeature(component):
    def RunScript(self, Beam, Geometry):
        if not Beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Geometry:
            self.AddRuntimeMessage(Warning, "Input parameter Geometry failed to collect data")
        if not (Beam and Geometry):
            return

        if not isinstance(Beam, list):
            Beam = [Beam]
        if not isinstance(Geometry, list):
            Geometry = [Geometry]

        FeatureDef = []
        for brep in Geometry:
            feature = BeamBooleanSubtraction(Brep.from_native(brep))
            FeatureDef.append(FeatureDefinition(feature, Beam))

        return FeatureDef
