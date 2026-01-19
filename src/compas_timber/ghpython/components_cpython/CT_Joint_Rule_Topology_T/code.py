# r: compas_timber>=1.0.1
# flake8: noqa
import inspect

import Grasshopper


from compas_timber.connections import PlateJoint
from compas_timber.connections import JointTopology
from compas_timber.connections import TButtJoint
from compas_timber.design import TopologyRule
from compas_timber.ghpython.ghcomponent_helpers import get_createable_joints
from compas_timber.ghpython.ghcomponent_helpers import manage_cpython_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class T_TopologyJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(T_TopologyJointRule, self).__init__()
        self.classes = {}
        for cls in get_createable_joints():
            supported_topo = cls.SUPPORTED_TOPOLOGY
            if JointTopology.TOPO_T == supported_topo and not issubclass(cls, PlateJoint):
                self.classes[cls.__name__] = cls
        self.joint_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Default: TButtJoint"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "TButtJoint is default, change in context menu (right click)")
            return TopologyRule(JointTopology.TOPO_T, TButtJoint)

        ghenv.Component.Message = self.joint_type.__name__
        kwargs = {}
        for i, val in enumerate(args):
            if val is not None:
                kwargs[self.arg_names()[i]] = val
        return TopologyRule(JointTopology.TOPO_T, self.joint_type, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][3:]
        return [name for name in names if (name != "key") and (name != "frame")] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
