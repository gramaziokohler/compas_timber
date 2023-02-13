# flake8: noqa
from ghpythonlib.componentbase import executingcomponent as component
import System
from compas_rhino.conversions import point_to_rhino


class MyComponent(component):
    def RunScript(self, Assembly):
        self.pt = []
        self.txt = []

        if not Assembly:
            return None
        for beam in Assembly.beams:
            self.pt.append(point_to_rhino(beam.midpoint))
            self.txt.append(str(beam.key))

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 16, "Verdana")
