# flake8: noqa
import Rhino.Geometry as rg
import System
from compas_rhino.conversions import frame_to_rhino
from ghpythonlib.componentbase import executingcomponent as component


class MyComponent(component):
    def RunScript(self, Beam):

        self.frame = [frame_to_rhino(b.frame) for b in Beam]
        self.scale = [b.width + b.height for b in Beam]

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return

        colorX = System.Drawing.Color.FromArgb(255, 255, 100, 100)
        colorY = System.Drawing.Color.FromArgb(200, 50, 220, 100)
        colorZ = System.Drawing.Color.FromArgb(200, 50, 150, 255)
        screensize = 10
        relativesize = 0

        for f, s in zip(self.frame, self.scale):
            arg.Display.DrawArrow(rg.Line(f.Origin, f.XAxis * s), colorX, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin, f.YAxis * s), colorY, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin, f.ZAxis * s), colorZ, screensize, relativesize)
