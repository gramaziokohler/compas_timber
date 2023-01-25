from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import LButtJoint
from compas_timber.ghpython import JointDefinition


class LButtDefinition(component):
    def RunScript(self, main_beam, cross_beam):
        if not main_beam:
            self.AddRuntimeMessage(Warning, "Input parameter main_beam failed to collect data.")
        if not cross_beam:
            self.AddRuntimeMessage(Warning, "Input parameter cross_beam failed to collect data.")
        if not (main_beam and cross_beam):
            return
        if not isinstance(main_beam, list):
            main_beam = [main_beam]
        if not isinstance(cross_beam, list):
            cross_beam = [cross_beam]
        if len(main_beam) != len(cross_beam):
            self.AddRuntimeMessage(Error, "Number of items in main_beam and cross_beam must match!")
            return

        joint_defs = []
        for main, cross in zip(main_beam, cross_beam):
            topology, _, _ = ConnectionSolver().find_topology(main, cross)
            if topology != LButtJoint.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        topology, LButtJoint.__name__
                    ),
                )
                continue
            joint_defs.append(JointDefinition(LButtJoint, [main_beam, cross_beam]))
        return joint_defs
