from compas.geometry import Brep
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import FeatureDefinition
from compas_timber.elements import BrepSubtraction


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

        f = BrepSubtraction(Brep.from_native(Geometry))
        Feature = FeatureDefinition(f, Beam)
        return Feature
