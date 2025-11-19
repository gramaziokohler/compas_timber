# r: compas_timber>=1.0.3
"""Defines which Joint type will be applied in the Automatic Joints component for connecting Beams with the given Category attributes. This overrides Topological Joint rules and is overriden by Direct joint rules"""

# flake8: noqa
import inspect
from collections import OrderedDict

import Grasshopper
from System.Windows.Forms import ToolStripSeparator

from compas_timber.connections import PlateJoint
from compas_timber.design import CategoryRule
from compas_timber.ghpython import get_leaf_subclasses
from compas_timber.ghpython import item_input_valid_cpython
from compas_timber.ghpython import manage_cpython_dynamic_params
from compas_timber.ghpython import rename_cpython_gh_output
from compas_timber.ghpython import warning
from compas_timber.ghpython import message


class CategoryPlateJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(CategoryPlateJointRule, self).__init__()

        self.classes = {}
        for cls in get_leaf_subclasses(PlateJoint):
            self.classes[cls.__name__] = cls

        self.joint_type = self.classes.get(self.component.Params.Output[0].NickName, None)

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
            if not item_input_valid_cpython(ghenv, cat_a, self.arg_names()[0]) or not item_input_valid_cpython(ghenv, cat_b, self.arg_names()[1]):
                return

            return CategoryRule(self.joint_type, cat_a, cat_b)

    def arg_names(self):
        names = inspect.getargspec(self.joint_type.__init__)[0][1:3]
        for i in range(2):
            names[i] += "_category"
        return [name for name in names if (name != "key") and (name != "frame")] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True
        menu.Items.Add(ToolStripSeparator())

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
