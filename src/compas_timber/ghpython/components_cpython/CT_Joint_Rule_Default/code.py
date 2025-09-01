# r: compas_timber>=1.0.0
import Grasshopper

from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.design import TopologyRule


class DefaultJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self):
        topoRules = []
        topoRules.append(TopologyRule(JointTopology.TOPO_L, LMiterJoint))
        topoRules.append(TopologyRule(JointTopology.TOPO_T, TButtJoint))
        topoRules.append(TopologyRule(JointTopology.TOPO_X, XLapJoint))

        return topoRules
