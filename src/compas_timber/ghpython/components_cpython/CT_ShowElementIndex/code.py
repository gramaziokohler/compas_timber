# flake8: noqa
import Grasshopper
import System

from compas_rhino.conversions import point_to_rhino


class ShowElementIndex(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not model:
            return None
        for element in model.beams + model.plates:
            self.pt.append(point_to_rhino(element.midpoint))
            self.txt.append(str(element.key))

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 16, "Verdana")
