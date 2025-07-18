# r: compas_timber>=0.15.3
"""Shows the names of the connection topology types."""

# flake8: noqa
import Grasshopper
import System
from compas_rhino.conversions import point_to_rhino
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import GenericJoint
from compas_timber.connections import MaxNCompositeAnalyzer

from compas_timber.connections import JointTopology
from compas_timber.utils import intersection_line_line_param
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class ShowTopologyTypes(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        self.pt = []
        self.txt = []

        if not item_input_valid_cpython(ghenv, model, "model"):
            return

        analyzer = MaxNCompositeAnalyzer(model, n=len(list(model.beams)))
        clusters = analyzer.find()

        for cluster in clusters:
            self.pt.append(cluster.joints[0].location)
            self.txt.append(cluster.joints[0].topology)

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(0, 0, 255, 0)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw2dText_5.htm
        for p, t in zip(self.pt, self.txt):
            arg.Display.Draw2dText(t, col, p, True, 12, "Verdana")
