# r: compas_timber>=0.15.3
# flake8: noqa
import inspect
from System.Windows.Forms import ToolStripSeparator

import Grasshopper

from compas_timber.connections import PlateJoint
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateMiterJoint
from compas_timber.design import TopologyRule
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class T_TopologyPlateJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(T_TopologyPlateJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(PlateJoint):
            if cls.SUPPORTED_TOPOLOGY == JointTopology.TOPO_T:
                self.classes[cls.__name__] = cls
        self.joint_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self):
        if not self.joint_type:
            ghenv.Component.Message = "Default: PlateMiterJoint"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "PlateMiterJoint is default, change in context menu (right click)")
            return TopologyRule(JointTopology.TOPO_T, PlateMiterJoint)
        else:
            ghenv.Component.Message = self.joint_type.__name__
            return TopologyRule(JointTopology.TOPO_T, self.joint_type)

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True
        menu.Items.Add(ToolStripSeparator())


    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        ghenv.Component.ExpireSolution(True)
