from compas_rhino.conversions import line_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import Drilling
from compas_timber.design import FeatureDefinition


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
        features = []
        for beam in beam:
            drilling = Drilling.from_line_and_beam(line, diameter, beam)
            features.append(FeatureDefinition(drilling, beam))
        return features
