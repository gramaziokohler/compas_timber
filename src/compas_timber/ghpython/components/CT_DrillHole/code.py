from compas_rhino.conversions import line_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import FeatureDefinition
from compas_timber.elements import DrillFeature


class DrillHoleFeature(component):
    def RunScript(self, Beam, Line, Diameter):
        if not Beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Line:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")

        if not (Beam and Line):
            return

        if not isinstance(Beam, list):
            Beam = [Beam]

        Diameter = Diameter or Beam[0].width * Beam[0].height * 0.5

        Line = line_to_compas(Line)
        f = DrillFeature(Line, Diameter, Line.length)
        Feature = FeatureDefinition(f, Beam)
        return Feature
