# flake8: noqa
import System
from compas_rhino.conversions import point_to_rhino
from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import JointTopology
from compas_timber.utils import intersection_line_line_param


class ShowTopologyTypes(component):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not model:
            return
        for topo in model.topologies:
            beam_a = topo["beam_a"]
            beam_b = topo["beam_b"]
            topology = topo.get("detected_topo")

            [p1, _], [p2, _] = intersection_line_line_param(beam_a.centerline, beam_b.centerline, float("inf"), False, 1e-3)
            p1 = point_to_rhino(p1)
            p2 = point_to_rhino(p2)
            self.pt.append((p2 + p1) / 2)
            self.txt.append(JointTopology.get_name(topology))

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(0, 0, 255, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
