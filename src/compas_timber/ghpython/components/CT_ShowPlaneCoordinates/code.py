__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
import System
import Rhino
import rhinoscriptsyntax as rs
from compas_rhino.conversions import point_to_rhino
import Rhino.Geometry as rg

class MyComponent(component):
    
    def RunScript(self, Pln):
        
        self.plane = Pln
        if not self.plane: return

    def DrawViewportWires(self,arg):
        if ghenv.Component.Locked: return
        
        colorX = System.Drawing.Color.FromArgb(255,255,100,100)
        colorY = System.Drawing.Color.FromArgb(200,50,220,100)
        colorZ = System.Drawing.Color.FromArgb(200,50,150,255)
        screensize = 10
        relativesize = 0
        
        f = self.plane
        if f:
            arg.Display.DrawArrow(rg.Line(f.Origin,f.XAxis), colorX, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin,f.YAxis), colorY, screensize, relativesize)
            arg.Display.DrawArrow(rg.Line(f.Origin,f.ZAxis), colorZ, screensize, relativesize)