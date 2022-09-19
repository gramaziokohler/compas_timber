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
from compas_timber.utils.compas_extra import intersection_line_line_3D


class MyComponent(component):
    
    def RunScript(self, JointsCollection):
        self.pt = []
        self.txt = []
        
        if not JointsCollection: return
        
        for jd in JointsCollection.objs:
            L1,L2 = [b.centreline for b in jd.beams]
            [p1,t1],[p2,t2] = intersection_line_line_3D(L1,L2, 0.2, False, 1e-3)
            p1 = point_to_rhino(p1)
            p2 = point_to_rhino(p2)
            
            self.pt.append((p2+p1)/2)
            self.txt.append(jd.joint_type)

    def DrawViewportWires(self,arg):
        if ghenv.Component.Locked: return
        col = System.Drawing.Color.FromArgb(255,0,0,0)
        #https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p,t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t,col,p,True,12,"Verdana")