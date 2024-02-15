from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_rhino.conversions import line_to_compas

from compas_timber.ghpython import FeatureDefinition
from compas_timber.parts import DrillFeature


class DrillHoleFeature(component):
    def RunScript(self, beam, line, diameter):
        if not beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not line:
            self.AddRuntimeMessage(Warning, "Input parameter Line failed to collect data")

        if not (beam and line):
            return

        if not isinstance(beam, list):
            beam = [beam]

        diameter = diameter or beam[0].width * beam[0].height * 0.5

        line = line_to_compas(line)
        f = DrillFeature(line, diameter, line.length)
        return FeatureDefinition(f, beam)
