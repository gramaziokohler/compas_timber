# r: compas_timber>=0.15.3
"""Generates a direct joint between two elements. This overrides other joint rules."""

import inspect

import Grasshopper  # type: ignore

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import SlabJoint
from compas_timber.connections import JointTopology
from compas_timber.design import DirectRule
from compas_timber.ghpython import error
from compas_timber.ghpython import get_leaf_subclasses
from compas_timber.ghpython import item_input_valid_cpython
from compas_timber.ghpython import manage_cpython_dynamic_params
from compas_timber.ghpython import rename_cpython_gh_output
from compas_timber.ghpython import warning


class DirectSlabJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(DirectSlabJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(SlabJoint):
            self.classes[cls.__name__] = cls

        if self.component.Params.Output[0].NickName not in self.classes.keys():
            self.joint_type = None
        else:
            self.joint_type = self.classes.get(self.component.Params.Output[0].NickName, None)

    @property
    def component(self):
        return ghenv.Component  # type: ignore  # noqa: F821

    def RunScript(self, *args):
        if not self.joint_type:
            self.component.Message = "Select joint type from context menu (right click)"
            warning(self.component, "Select joint type from context menu (right click)")
            return None
        else:
            self.component.Message = self.joint_type.__name__
            slab_a = args[0]
            slab_b = args[1]
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val

            if not item_input_valid_cpython(ghenv, slab_a, self.arg_names()[0]) or not item_input_valid_cpython(ghenv, slab_b, self.arg_names()[1]):
                return
            if not hasattr(slab_a, "__iter__"):
                slab_a = [slab_a]
            if not hasattr(slab_b, "__iter__"):
                slab_b = [slab_b]
            if len(slab_a) != len(slab_b):
                error(self.component, f"Number of items in {self.arg_names()[0]} and {self.arg_names()[1]} must match!")
                return
            Rules = []
            for main, secondary in zip(slab_a, slab_b):
                Rules.append(DirectRule(self.joint_type, [secondary, main], **kwargs))
            return Rules

    def arg_names(self):
        return inspect.getargspec(self.joint_type.__init__)[0][1:] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        self.component.ExpireSolution(True)
