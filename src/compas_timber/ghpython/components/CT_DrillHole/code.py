from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_rhino.conversions import line_to_compas

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import DrillFeature


class DrillHoleFeature(component):
    def RunScript(self, beam, line, diameter, length):
        if not beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not line:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")
        if not diameter:
            self.AddRuntimeMessage(Warning, "Input parameter Diameter failed to collect data")
        if not length:
            self.AddRuntimeMessage(Warning, "Input parameter Length failed to collect data")

        if not (beam and line and diameter and length):
            return

        if not isinstance(beam, list):
            beam = [beam]

        f = DrillFeature(line_to_compas(line), diameter, length)
        return FeatureDefinition(f, beam)
