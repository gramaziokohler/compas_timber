from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import TButtJoint
from compas_timber.ghpython import JointDefinition


class TButtDefinition(component):
    def RunScript(self, main_beam, cross_beam):
        if not (main_beam and cross_beam):
            return

        topology, _, _ = ConnectionSolver().find_topology(main_beam, cross_beam)

        if topology != TButtJoint.SUPPORTED_TOPOLOGY:
            self.AddRuntimeMessage(
                    Warning, "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        topology, TButtJoint.__name__
                    )
                )

        return JointDefinition(TButtJoint, [main_beam, cross_beam])

