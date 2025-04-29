# r: compas_timber>=0.15.3
"""Shows the names of the connection topology types."""

# flake8: noqa
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
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b)
            if not detected_topo == JointTopology.TOPO_UNKNOWN:
                topologies.append({"detected_topo": detected_topo, "beam_a": beam_a, "beam_b": beam_b})

        for topo in topologies:
            beam_a = topo["beam_a"]
            beam_b = topo["beam_b"]
            topology = topo.get("detected_topo")

            [p1, _], [p2, _] = intersection_line_line_param(beam_a.centerline, beam_b.centerline, float("inf"), False, 1e-3)
            p1 = point_to_rhino(p1)
            p2 = point_to_rhino(p2)
            self.pt.append((p2 + p1) / 2)
            self.txt.append(JointTopology.get_name(topology))

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(0, 0, 255, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
