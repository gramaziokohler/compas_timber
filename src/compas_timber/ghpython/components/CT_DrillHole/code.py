from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_rhino.conversions import line_to_compas

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import DrillFeature


class DrillHoleFeature(component):
    def RunScript(self, Beam, Line, Diameter, Length):
        if not Beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Line:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")
        if not Diameter:
            self.AddRuntimeMessage(Warning, "Input parameter Diameter failed to collect data")
        if not Length:
            self.AddRuntimeMessage(Warning, "Input parameter Length failed to collect data")

        if not (Beam and Line and Diameter and Length):
            return

        if not isinstance(Beam, list):
            Beam = [Beam]

        Feature = []
        for beam in Beam:
            feature = DrillFeature(line_to_compas(Line), Diameter, Length)
            Feature.append(FeatureDefinition(feature, beam))

        return Feature
