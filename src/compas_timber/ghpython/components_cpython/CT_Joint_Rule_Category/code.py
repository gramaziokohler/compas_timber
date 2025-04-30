# r: compas_timber>=0.15.3
"""Defines which Joint type will be applied in the Automatic Joints component for connecting Beams with the given Category attributes. This overrides Topological Joint rules and is overriden by Direct joint rules"""

# flake8: noqa
import inspect
from collections import OrderedDict

import Grasshopper
from System.Windows.Forms import ToolStripMenuItem
from System.Windows.Forms import ToolStripSeparator

from compas_timber.connections import Joint
from compas_timber.design import CategoryRule
from compas_timber.ghpython import get_leaf_subclasses
from compas_timber.ghpython import item_input_valid_cpython
from compas_timber.ghpython import manage_cpython_dynamic_params
from compas_timber.ghpython import rename_cpython_gh_output
from compas_timber.ghpython import warning
from compas_timber.ghpython import message


class CategoryJointRule(Grasshopper.Kernel.GH_ScriptInstance):
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

    @property
    def component(self):
        return ghenv.Component  # type: ignore

    def RunScript(self, *args):
        if not self.joint_type:
            warning(self.component, "Select joint type from context menu (right click)")
            return None
        else:
            message(self.component, self.joint_type.__name__)
            cat_a, cat_b = args[:2]
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val
            if not item_input_valid_cpython(ghenv, cat_a, self.arg_names()[0]) or not item_input_valid_cpython(ghenv, cat_b, self.arg_names()[1]):
                return

            topos = []
            for i, bool in enumerate(self.topo_bools.values()):
                if bool:
                    topos.append(i)

            return CategoryRule(self.joint_type, cat_a, cat_b, topos, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][1:]
        for i in range(2):
            names[i] += "_category"
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
        rename_cpython_gh_output(self.output_name(), 0, ghenv)
        ghenv.Component.ExpireSolution(True)

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.output_name(), 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=2)
        ghenv.Component.ExpireSolution(True)
