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
from compas_timber.ghpython.ghcomponent_helpers import manage_cpython_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class EdgeEdgeTopologyPlateJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(EdgeEdgeTopologyPlateJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(PlateJoint):
            if cls.SUPPORTED_TOPOLOGY == JointTopology.TOPO_EDGE_EDGE:
                self.classes[cls.__name__] = cls
        self.joint_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Default: PlateMiterJoint"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "PlateMiterJoint is default, change in context menu (right click)")
            return TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint)
        else:
            ghenv.Component.Message = self.joint_type.__name__
            kwargs = {}
            for i, val in enumerate(args):
                if val is not None:
                    kwargs[self.arg_names()[i]] = val
            ghenv.Component.Message = self.joint_type.__name__
            return TopologyRule(JointTopology.TOPO_EDGE_EDGE, self.joint_type, **kwargs)

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True
        menu.Items.Add(ToolStripSeparator())

    def arg_names(self):
        return ["max_distance"]

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
