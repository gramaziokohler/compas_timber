from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import JointTopology
from compas_timber.ghpython import TopologyRule

from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint


class MyComponent(component):
    def RunScript(self, L, T, X):
        topoRules = []




        if L:
            if not L.type.SUPPORTED_TOPOLOGY == JointTopology.TOPO_L:
                self.AddRuntimeMessage(Warning, "Joint type does not match topology. Joint may not be generated.")
            topoRules.append(TopologyRule(JointTopology.TOPO_L, L.type, **L.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_L, LMiterJoint))
        if T:
            if not T.type.SUPPORTED_TOPOLOGY == JointTopology.TOPO_T:
                self.AddRuntimeMessage(Warning, "Joint type does not match topology. Joint may not be generated.")
            topoRules.append(TopologyRule(JointTopology.TOPO_T, T.type, **T.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_T, TButtJoint))
        if X:
            if not X.type.SUPPORTED_TOPOLOGY == JointTopology.TOPO_X:
                self.AddRuntimeMessage(Warning, "Joint type does not match topology. Joint may not be generated.")
            topoRules.append(TopologyRule(JointTopology.TOPO_X, X.type, **X.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_X, XHalfLapJoint))

        return topoRules
