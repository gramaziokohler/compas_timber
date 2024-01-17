from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import JointTopology
from compas_timber.ghpython import TopologyRule

from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint


class MyComponent(component):
    def RunScript(self, L, T, X):
        topoRules = []

        if L:
            topoRules.append(TopologyRule(JointTopology.TOPO_L, L.type, **L.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_L, LMiterJoint))
        if T:
            topoRules.append(TopologyRule(JointTopology.TOPO_T, T.type, **T.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_T, TButtJoint))
        if X:
            topoRules.append(TopologyRule(JointTopology.TOPO_X, X.type, **X.kwargs))
        else:
            topoRules.append(TopologyRule(JointTopology.TOPO_X, XHalfLapJoint))

        return topoRules
