# flake8: noqa
import System
from compas_rhino.conversions import point_to_rhino
from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.utils import intersection_line_line_param


class ShowJointTypes(component):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not model:
            return

        for joint in model.joints:
            line_a, line_b = joint.beams[0].centerline, joint.beams[1].centerline
            [p1, t1], [p2, t2] = intersection_line_line_param(line_a, line_b, float("inf"), False, 1e-3)
            p1 = point_to_rhino(p1)
            p2 = point_to_rhino(p2)

            self.pt.append((p2 + p1) / 2)
            self.txt.append(joint.__class__.__name__)

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 0, 0, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
