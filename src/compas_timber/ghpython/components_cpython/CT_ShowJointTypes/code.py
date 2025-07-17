# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System
from compas_rhino.conversions import point_to_rhino

from compas_timber.utils import intersection_line_line_param
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class ShowJointTypes(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not item_input_valid_cpython(ghenv, model, "model"):
            return

        for joint in model.joints:
            line_a, line_b = joint.elements[0].centerline, joint.elements[1].centerline
            [p1, _], [p2, _] = intersection_line_line_param(line_a, line_b, float("inf"), False, 1e-3)
            p1 = point_to_rhino(p1)
            p2 = point_to_rhino(p2)

            self.pt.append((p2 + p1) / 2)
            self.txt.append(joint.__class__.__name__)

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 0, 0, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
