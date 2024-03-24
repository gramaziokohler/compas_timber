from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import JointTopology
from compas_timber.ghpython import TopologyRule

from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint


class DefaultJointRule(component):
    def RunScript(self):
        topoRules = []
        topoRules.append(TopologyRule(JointTopology.TOPO_L, LMiterJoint))
        topoRules.append(TopologyRule(JointTopology.TOPO_T, TButtJoint))
        topoRules.append(TopologyRule(JointTopology.TOPO_X, XHalfLapJoint))

        return topoRules
