from compas.geometry import Brep
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import FeatureDefinition
from compas_timber.elements import BrepSubtraction


class BrepSubtractionFeature(component):
    def RunScript(self, beam, geometry):
        if not beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not geometry:
            self.AddRuntimeMessage(Warning, "Input parameter Geometry failed to collect data")
        if not (beam and geometry):
            return

        if not isinstance(beam, list):
            beam = [beam]

        feature = BrepSubtraction(Brep.from_native(geometry))
        return FeatureDefinition(feature, beam)
