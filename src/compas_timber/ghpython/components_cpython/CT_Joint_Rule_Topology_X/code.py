# r: compas_timber>=0.15.3
# flake8: noqa
import inspect

import Grasshopper

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections import XLapJoint
from compas_timber.design import TopologyRule
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_cpython_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class X_TopologyJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(X_TopologyJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
            supported_topo = cls.SUPPORTED_TOPOLOGY
            if not isinstance(supported_topo, list):
                supported_topo = [supported_topo]
            if JointTopology.TOPO_X in supported_topo:
                self.classes[cls.__name__] = cls
        if ghenv.Component.Params.Output[0].NickName == "Rule":
            self.joint_type = XLapJoint
            self.clicked = False
        else:
            self.joint_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)
            self.clicked = True

    def RunScript(self, *args):
        if not self.clicked:
            ghenv.Component.Message = "Default: XLapJoint"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "XLapJoint is default, change in context menu (right click)")
            return TopologyRule(JointTopology.TOPO_X, XLapJoint)
        else:
            ghenv.Component.Message = self.joint_type.__name__
            kwargs = {}
            for i, val in enumerate(args):
                if val is not None:
                    kwargs[self.arg_names()[i]] = val
            supported_topo = self.joint_type.SUPPORTED_TOPOLOGY
            if not isinstance(supported_topo, list):
                supported_topo = [supported_topo]
            if JointTopology.TOPO_X not in supported_topo:
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Joint type does not match topology. Joint may not be generated.")
            return TopologyRule(JointTopology.TOPO_X, self.joint_type, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][3:]
        return [name for name in names if (name != "key") and (name != "frame")] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.clicked = True
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
