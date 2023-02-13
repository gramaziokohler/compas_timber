import Rhino.Geometry as rg
import System
from ghpythonlib.componentbase import executingcomponent as component


class ShowPlaneCoordinates(component):
    def RunScript(self, Pln):
        self.plane = Pln
        if not self.plane:
            return

    def DrawViewportWires(self, arg):
        if self.Locked:  # noqa: F821
            return

        colorX = System.Drawing.Color.FromArgb(255, 255, 100, 100)
        colorY = System.Drawing.Color.FromArgb(200, 50, 220, 100)
        colorZ = System.Drawing.Color.FromArgb(200, 50, 150, 255)
        screensize = 10
        relativesize = 0

        f = self.plane
        if f:
            arg.Display.DrawArrow(rg.Line(f.Origin, f.XAxis), colorX, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin, f.YAxis), colorY, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin, f.ZAxis), colorZ, screensize, relativesize)
