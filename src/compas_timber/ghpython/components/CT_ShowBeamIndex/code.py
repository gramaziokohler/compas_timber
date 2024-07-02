# flake8: noqa
import System
from compas_rhino.conversions import point_to_rhino
from ghpythonlib.componentbase import executingcomponent as component


class ShowBeamIndex(component):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not model:
            return None
        for beam in model.beams:
            self.pt.append(point_to_rhino(beam.midpoint))
            self.txt.append(str(beam.key))

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 16, "Verdana")
