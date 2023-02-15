from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import LMiterJoint
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition


class LMiterDefinition(component):
    def RunScript(self, BeamA, BeamB):
        if not BeamA:
            self.AddRuntimeMessage(Warning, "Input parameter BeamA failed to collect data.")
        if not BeamB:
            self.AddRuntimeMessage(Warning, "Input parameter BeamB failed to collect data.")
        if not (BeamA and BeamB):
            return
        if not isinstance(BeamA, list):
            BeamA = [BeamA]
        if not isinstance(BeamB, list):
            BeamB = [BeamB]
        if len(BeamA) != len(BeamB):
            self.AddRuntimeMessage(Error, "Number of items in BeamA and BeamB must match!")
            return

        JointDef = []
        for main, cross in zip(BeamA, BeamB):
            topology, _, _ = ConnectionSolver().find_topology(main, cross)
            if topology != LMiterJoint.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        JointTopology.get_name(topology), LMiterJoint.__name__
                    ),
                )
                continue
            JointDef.append(JointDefinition(LMiterJoint, [BeamA, BeamB]))
        return JointDef
