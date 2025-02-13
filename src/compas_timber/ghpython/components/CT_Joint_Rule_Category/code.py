import inspect
from collections import OrderedDict

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from System.Windows.Forms import ToolStripMenuItem
from System.Windows.Forms import ToolStripSeparator

from compas_timber.connections import Joint
from compas_timber.design import CategoryRule
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class CategoryJointRule(component):
    def __init__(self):
        super(CategoryJointRule, self).__init__()
        self.topo_bools = OrderedDict([("Unknown", False), ("I", False), ("L", False), ("T", False), ("X", False)])

        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
            self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Rule":
            self.joint_type = None
        else:
            parsed_output = ghenv.Component.Params.Output[0].NickName.split("_")
            self.joint_type = self.classes.get(parsed_output[0])
            for key in parsed_output[1:]:
                self.topo_bools[key] = True

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
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val
            if not cat_a:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0]))
            if not cat_b:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[1]))
            if not (cat_a and cat_b):
                return

            topos = []
            for i, bool in enumerate(self.topo_bools.values()):
                if bool:
                    topos.append(i)

            return CategoryRule(self.joint_type, cat_a, cat_b, topos, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][1:]
        for i in range(2):
            names[i] += " category"
        return [name for name in names if (name != "key") and (name != "frame")] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

        menu.Items.Add(ToolStripSeparator())
        topo_menu = ToolStripMenuItem("Apply to Topology")
        menu.Items.Add(topo_menu)
        for name, bool in self.topo_bools.items():
            item = ToolStripMenuItem(name, None, self.on_topo_click)
            item.Checked = bool
            topo_menu.DropDownItems.Add(item)

    def output_name(self):
        name = self.joint_type.__name__
        for key, bool in self.topo_bools.items():
            if bool:
                name += "_{}".format(key)
        return name

    def on_topo_click(self, sender, event_info):
        self.topo_bools[str(sender)] = not self.topo_bools[str(sender)]
        rename_gh_output(self.output_name(), 0, ghenv)
        ghenv.Component.ExpireSolution(True)

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_gh_output(self.output_name(), 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
