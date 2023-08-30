from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import XHalfLapJoint
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition


class XHalfLapDefinition(component):
    def RunScript(self, MainBeam, CrossBeam):
        if not MainBeam:
            self.AddRuntimeMessage(Warning, "Input parameter MainBeams failed to collect data.")
        if not CrossBeam:
            self.AddRuntimeMessage(Warning, "Input parameter CrossBeams failed to collect data.")
        if not (MainBeam and CrossBeam):
            return
        if not isinstance(MainBeam, list):
            MainBeam = [MainBeam]
        if not isinstance(CrossBeam, list):
            CrossBeam = [CrossBeam]
        if len(MainBeam) != len(CrossBeam):
            self.AddRuntimeMessage(Error, "Number of items in MainBeams and CrossBeams must match!")
            return

        Joint = []
        for main, cross in zip(MainBeam, CrossBeam):
            topology, _, _ = ConnectionSolver().find_topology(main, cross)
            if topology != XHalfLapJoint.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        JointTopology.get_name(topology), XHalfLapJoint.__name__
                    ),
                )
                continue
            Joint.append(JointDefinition(XHalfLapJoint, [main, cross]))
        return Joint
