from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import TButtJoint
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition


class LMiterDefinition(component):
    def RunScript(self, MainBeam, CrossBeam):
        if not MainBeam:
            self.AddRuntimeMessage(Warning, "Input parameter MainBeam failed to collect data.")
        if not CrossBeam:
            self.AddRuntimeMessage(Warning, "Input parameter CrossBeam failed to collect data.")
        if not (MainBeam and CrossBeam):
            return
        if not isinstance(MainBeam, list):
            MainBeam = [MainBeam]
        if not isinstance(CrossBeam, list):
            CrossBeam = [CrossBeam]
        if len(MainBeam) != len(CrossBeam):
            self.AddRuntimeMessage(Error, "Number of items in MainBeam and CrossBeam must match!")
            return

        JointDefs = []
        for main, cross in zip(MainBeam, CrossBeam):
            topology, _, _ = ConnectionSolver().find_topology(main, cross)
            if topology != TButtJoint.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        JointTopology.get_name(topology), TButtJoint.__name__
                    ),
                )
                continue
            JointDefs.append(JointDefinition(TButtJoint, [MainBeam, CrossBeam]))
        return JointDefs
