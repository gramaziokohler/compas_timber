from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import clr
import System
import inspect

from compas_timber.connections import Joint
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import get_all_subclasses
from compas_timber.ghpython import CategoryRule


class CategoryJointRule(component):
    def __init__(self):
        super(CategoryJointRule, self).__init__()
        self.classes =  {}
        for cls in get_all_subclasses(Joint):
            self.classes[cls.__name__] = cls
        self.items = []
        self.joint_type = None
        self.joint_name = None


    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Select joint type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select joint type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.joint_name
            cat_a = args[0]
            cat_b = args[1]

            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val:
                    kwargs[self.arg_names()[i+2]] = val
            print(kwargs)
            if not cat_a:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0]))
            if not cat_b:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[1]))
            if not (cat_a and cat_b):
                return

            return CategoryRule(self.joint_type, cat_a, cat_b, **kwargs)


    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][1:]
        for i in range(2):
            names[i] += " category"
        return names


    def AppendAdditionalMenuItems(self, menu):
        if self.items:
            for item in self.items:
                menu.Items.Add(item)
        else:
            for name in self.classes.keys():
                item = menu.Items.Add(name, None, self.on_item_click)
                self.items.append(item)


    def on_item_click(self, sender, event_info):
        active_item = clr.Convert(sender, System.Windows.Forms.ToolStripItem)
        active_item.Checked = True

        for item in self.items:
            if str(item) != str(sender):
                item.Checked = False

        self.joint_name = str(sender)
        self.joint_type = self.classes[self.joint_name]

        manage_dynamic_params(self.arg_names(), ghenv, rename_count = 2, permanent_param_count = 0)
        ghenv.Component.ExpireSolution(True)
