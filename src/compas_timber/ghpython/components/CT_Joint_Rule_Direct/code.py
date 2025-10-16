import inspect

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import DirectRule
from compas_timber.ghpython.ghcomponent_helpers import get_createable_joints
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class DirectJointRule(component):
    def __init__(self):
        super(DirectJointRule, self).__init__()
        self.classes = {}
        for cls in get_createable_joints():
            if cls.MAX_ELEMENT_COUNT == 2:
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
            beam_a = args[0]
            beam_b = args[1]

            if not beam_a:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0]))
            if not beam_b:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[1]))
            if not (args[0] and args[1]):
                return

            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val

            Rules = DirectRule(self.joint_type, [beam_a, beam_b], **kwargs)
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
        rename_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
