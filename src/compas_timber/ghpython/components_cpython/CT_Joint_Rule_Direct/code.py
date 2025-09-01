# r: compas_timber>=1.0.0
"""Generates a direct joint between two elements. This overrides other joint rules."""

import inspect

import Grasshopper  # type: ignore

from compas_timber.connections import Joint
from compas_timber.connections import PlateJoint
from compas_timber.design import DirectRule
from compas_timber.ghpython import error
from compas_timber.ghpython import get_leaf_subclasses
from compas_timber.ghpython import item_input_valid_cpython
from compas_timber.ghpython import manage_cpython_dynamic_params
from compas_timber.ghpython import rename_cpython_gh_output
from compas_timber.ghpython import warning


class DirectJointRule(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(DirectJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
            if cls.MAX_ELEMENT_COUNT == 2 and not issubclass(cls, PlateJoint):
                self.classes[cls.__name__] = cls

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
            beam_a = args[0]
            beam_b = args[1]
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val

            if not item_input_valid_cpython(ghenv, beam_a, self.arg_names()[0]) or not item_input_valid_cpython(ghenv, beam_b, self.arg_names()[1]):
                return
            if not hasattr(beam_a, "__iter__"):
                beam_a = [beam_a]
            if not hasattr(beam_b, "__iter__"):
                beam_b = [beam_b]
            if len(beam_a) != len(beam_b):
                error(self.component, f"Number of items in {self.arg_names()[0]} and {self.arg_names()[1]} must match!")
                return
            Rules = []
            for main, secondary in zip(beam_a, beam_b):  # TODO: grasshopper should handle this
                # TODO: figure out where to do TOPO checks. I think in JointRules.
                Rules.append(DirectRule(self.joint_type, [main, secondary], **kwargs))
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
