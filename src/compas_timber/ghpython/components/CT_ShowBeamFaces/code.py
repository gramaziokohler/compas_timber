# flake8: noqa
import System
from compas_rhino.conversions import point_to_rhino
from ghpythonlib.componentbase import executingcomponent as component


class ShowBeamFaces(component):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not model:
            return None
        for beam in model.beams:
            for f_index, face in enumerate(beam.faces):
                self.pt.append(point_to_rhino(face.point))
                self.txt.append(str(f_index))

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 16, "Verdana")
