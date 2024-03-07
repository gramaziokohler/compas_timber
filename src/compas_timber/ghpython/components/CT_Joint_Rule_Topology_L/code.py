
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import clr
import System
import inspect

from compas_timber.connections import Joint
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import get_all_subclasses
from compas_timber.ghpython import CategoryRule

from compas_timber.connections import JointTopology
from compas_timber.ghpython import TopologyRule

from compas_timber.connections import LMiterJoint



class L_TopologyJointRule(component):
    def __init__(self):
        super(L_TopologyJointRule, self).__init__()
        self.classes =  {}
        for cls in get_all_subclasses(Joint):
            self.classes[cls.__name__] = cls
        self.items = []
        self.joint_type = None
        self.joint_name = 'LMiterJoint'
        self.clicked = False


    def RunScript(self, *args):
        if not self.clicked:
            ghenv.Component.Message = "Default: LMiterJoint"
            self.AddRuntimeMessage(Warning, "LMiterJoint is default, change in context menu (right click)")
            return (TopologyRule(JointTopology.TOPO_L, LMiterJoint))
        else:
            ghenv.Component.Message = self.joint_name
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val:
                    kwargs[self.arg_names()[i+2]] = val
            if self.joint_type.SUPPORTED_TOPOLOGY != JointTopology.TOPO_L:
                self.AddRuntimeMessage(Warning, "Joint type does not match topology. Joint may not be generated.")
            return (TopologyRule(JointTopology.TOPO_L, self.joint_type, **kwargs))


    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][3:]
        return [name for name in names if (name != 'key') and (name != 'frame')]


    def AppendAdditionalMenuItems(self, menu):
        if self.items:
            for item in self.items:
                menu.Items.Add(item)
        else:
            for name in self.classes.keys():
                item = menu.Items.Add(name, None, self.on_item_click)
                if name == "LMiterJoint":
                    item.Checked = True
                self.items.append(item)


    def on_item_click(self, sender, event_info):
        active_item = clr.Convert(sender, System.Windows.Forms.ToolStripItem)
        active_item.Checked = True
        self.clicked = True
        for item in self.items:
            if str(item) != str(sender):
                item.Checked = False

        self.joint_name = str(sender)
        self.joint_type = self.classes[self.joint_name]

        manage_dynamic_params(self.arg_names(), ghenv, rename_count = 0, permanent_param_count = 0)
        ghenv.Component.ExpireSolution(True)
