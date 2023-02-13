from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import LButtJoint
from compas_timber.ghpython import JointDefinition


class LButtDefinition(component):
    def RunScript(self, MainBeams, CrossBeams):
        if not MainBeams:
            self.AddRuntimeMessage(Warning, "Input parameter MainBeams failed to collect data.")
        if not CrossBeams:
            self.AddRuntimeMessage(Warning, "Input parameter CrossBeams failed to collect data.")
        if not (MainBeams and CrossBeams):
            return
        if not isinstance(MainBeams, list):
            MainBeams = [MainBeams]
        if not isinstance(CrossBeams, list):
            CrossBeams = [CrossBeams]
        if len(MainBeams) != len(CrossBeams):
            self.AddRuntimeMessage(Error, "Number of items in MainBeams and CrossBeams must match!")
            return

        JointDefs = []
        for main, cross in zip(MainBeams, CrossBeams):
            topology, _, _ = ConnectionSolver().find_topology(main, cross)
            if topology != LButtJoint.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        topology, LButtJoint.__name__
                    ),
                )
                continue
            JointDefs.append(JointDefinition(LButtJoint, [MainBeams, CrossBeams]))
        return JointDefs
