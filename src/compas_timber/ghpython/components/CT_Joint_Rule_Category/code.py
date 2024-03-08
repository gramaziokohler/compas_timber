from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import inspect

from compas_timber.connections import Joint
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import rename_GH_output
from compas_timber.ghpython import CategoryRule


class CategoryJointRule(component):
    def __init__(self):
        super(CategoryJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
            self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Rule":
            self.joint_type = None
        else:
            self.joint_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Select joint type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select joint type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.joint_type.__name__
            cat_a = args[0]
            cat_b = args[1]

            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val:
                    kwargs[self.arg_names()[i + 2]] = val
            print(kwargs)
            if not cat_a:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0])
                )
            if not cat_b:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[1])
                )
            if not (cat_a and cat_b):
                return

            return CategoryRule(self.joint_type, cat_a, cat_b, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][1:]
        for i in range(2):
            names[i] += " category"
        return [name for name in names if (name != "key") and (name != "frame")]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_GH_output(self.joint_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
