# r: compas_timber>=1.0.0
"""Shows the names of the connection topology types."""

# flake8: noqa
import re
import Grasshopper
import System
from compas_rhino.conversions import point_to_rhino
from compas_timber.connections import ConnectionSolver

from compas_timber.connections import JointTopology
from compas_timber.utils import intersection_line_line_param
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class ShowTopologyTypes(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not item_input_valid_cpython(ghenv, model, "model"):
            return

        topologies = []
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(list(model.beams), rtree=True)
        for pair in found_pairs:
            result = solver.find_topology(*pair)
            if not result.topology == JointTopology.TOPO_UNKNOWN:
                self.pt.append(point_to_rhino(result.point))
                self.txt.append(JointTopology.get_name(result.topology))

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(0, 0, 255, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
