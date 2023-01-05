from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
import System
import Rhino
import rhinoscriptsyntax as rs
from compas_rhino.conversions import point_to_rhino
import Rhino.Geometry as rg

class MyComponent(component):
    
    def RunScript(self, assembly):
        
        self.pt = []
        self.txt = []
        
        if not assembly: 
            return
        for beam in assembly.beams:
            self.pt.append(point_to_rhino(beam.midpoint))
            self.txt.append(str(beam.key))

    def DrawViewportWires(self,arg):
        if ghenv.Component.Locked: return
        col = System.Drawing.Color.FromArgb(255,255,255,255)
        #https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p,t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t,col,p,True,16,"Verdana")
