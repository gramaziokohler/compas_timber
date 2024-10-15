# flake8: noqa
import System
from compas_rhino.conversions import point_to_rhino
from ghpythonlib.componentbase import executingcomponent as component


class ShowBeamFaces(component):
    def RunScript(self, Beam):
        self.pt = []
        self.txt = []

        if not Beam:
            return None
        for b in Beam:
            for side_index in range(len(b.ref_sides)):
                surface = b.side_as_surface(side_index)
                midpoint = surface.point_at(surface.xsize * 0.5, surface.ysize * 0.5)
                side_name = b.ref_sides[side_index].name

                self.pt.append(point_to_rhino(midpoint))
                self.txt.append(side_name)

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 16, "Verdana")
