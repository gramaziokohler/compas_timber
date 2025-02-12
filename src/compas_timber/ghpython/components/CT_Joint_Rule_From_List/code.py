import inspect

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import Joint
from compas_timber.design import DirectRule
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class JointRuleFromList(component):
    def __init__(self):
        super(JointRuleFromList, self).__init__()
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
            elements = args[0]
            if not elements:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names[0]))
                return
            if not self.joint_type.element_count_complies(elements):
                self.AddRuntimeMessage(
                    Warning,
                    "{} requires at least {} and at most {} elements.".format(self.joint_type.__name__, self.joint_type.MIN_ELEMENT_COUNT, self.joint_type.MAX_ELEMENT_COUNT),
                )
                return
            kwargs = {}
            for i, val in enumerate(args[1:]):
                if val is not None:
                    kwargs[self.arg_names[i]] = val

            return DirectRule(self.joint_type, elements, **kwargs)

    @property
    def arg_start_index(self):
        if self.joint_type.MAX_ELEMENT_COUNT is None:
            return 2
        elif self.joint_type.MAX_ELEMENT_COUNT == self.joint_type.MIN_ELEMENT_COUNT:
            return self.joint_type.MAX_ELEMENT_COUNT + 1
        else:
            raise Error("I don't know how to handle this joint type")

    @property
    def arg_names(self):
        return inspect.getargspec(self.joint_type.__init__)[0][self.arg_start_index :] + ["max_distance"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.joint_type and name == self.joint_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.joint_type = self.classes[str(sender)]
        rename_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names, ghenv, permanent_param_count=1)
        ghenv.Component.ExpireSolution(True)
