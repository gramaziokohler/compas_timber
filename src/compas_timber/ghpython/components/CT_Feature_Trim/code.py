from compas_rhino.conversions import plane_to_compas_frame
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import BeamTrimmingFeature


class TrimmingFeature(component):
    def RunScript(self, Beam, Plane):
        if not Beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beam failed to collect data")
        if not Plane:
            self.AddRuntimeMessage(Warning, "Input parameter Plane failed to collect data")
        if not (Beam and Plane):
            return

        if not isinstance(Beam, list):
            Beam = [Beam]
        if not isinstance(Plane, list):
            Plane = [Plane]

        Feature = []
        for plane in Plane:
            feature = BeamTrimmingFeature(plane_to_compas_frame(plane))
            Feature.append(FeatureDefinition(feature, Beam))

        return Feature

