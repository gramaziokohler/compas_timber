# r: compas_timber>=0.15.3
# flake8: noqa
import inspect

import Grasshopper
from System.Windows.Forms import ToolStripMenuItem
from System.Windows.Forms import ToolStripSeparator

from compas_timber.connections import Joint
from compas_timber.design import CategoryRule
from compas_timber.design import SurfaceModel
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_cpython_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class SurfaceModelJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(SurfaceModelJointRule, self).__init__()
        self.cat_a = None
        self.cat_b = None
        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
            self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Rule":
            self.joint_type = None
        else:
            parsed_output = ghenv.Component.Params.Output[0].NickName.split(" ")
            self.joint_type = self.classes.get(parsed_output[0])
            if len(parsed_output) > 1:
                self.cat_a = parsed_output[1]
            if len(parsed_output) > 2:
                self.cat_b = parsed_output[2]

    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Select joint type from context menu (right click)"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Select joint type from context menu (right click)")
            return None

        else:
            ghenv.Component.Message = self.joint_type.__name__

            kwargs = {}
            for i, val in enumerate(args):
                if val:
                    kwargs[self.arg_names()[i + 2]] = val

            return CategoryRule(self.joint_type, self.cat_a, self.cat_b, **kwargs)

    def arg_names(self):
        if self.joint_type:
            names = inspect.getargspec(self.joint_type.__init__)[0][1:]
        else:
            names = ["beam_a", "beam_b"]
        for i in range(2):
            names[i] += " category"
        return [name for name in names if (name != "key") and (name != "frame")]

    def AppendAdditionalMenuItems(self, menu):
        if not self.RuntimeMessages(Warning):
            menu.Items.Add(ToolStripSeparator())
        beam_a_menu = ToolStripMenuItem(self.arg_names()[0])
        menu.Items.Add(beam_a_menu)
        for name in SurfaceModel.beam_category_names():
            item = ToolStripMenuItem(name, None, self.on_beam_a_click)
            if name == self.cat_a:
                item.Checked = True
            beam_a_menu.DropDownItems.Add(item)

        beam_b_menu = ToolStripMenuItem(self.arg_names()[1])
        menu.Items.Add(beam_b_menu)
        for name in SurfaceModel.beam_category_names():
            item = ToolStripMenuItem(name, None, self.on_beam_b_click)
            if name == self.cat_b:
                item.Checked = True
            beam_b_menu.DropDownItems.Add(item)
        menu.Items.Add(ToolStripSeparator())
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def output_name(self):
        name = self.joint_type.__name__
        if self.cat_a:
            name += " {}".format(self.cat_a)
        if self.cat_b:
            name += " {}".format(self.cat_b)
        return name

    def on_beam_a_click(self, sender, event_info):
        self.cat_a = sender.Text
        rename_cpython_gh_output(self.output_name(), 0, ghenv)
        ghenv.Component.ExpireSolution(True)

    def on_beam_b_click(self, sender, event_info):
        self.cat_b = sender.Text
        rename_cpython_gh_output(self.output_name(), 0, ghenv)
        ghenv.Component.ExpireSolution(True)

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.output_name(), 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names()[2:], ghenv, rename_count=0, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
