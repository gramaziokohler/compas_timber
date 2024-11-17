import inspect

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.design import DirectRule
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class ManyJointRule(component):
    def __init__(self):
        super(ManyJointRule, self).__init__()
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
            if not self.joint_type.SUPPORTED_TOPOLOGY in range (1,5):
                beams = args[0]
                if not beams:
                    self.AddRuntimeMessage(
                        Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0])
                    )
                    return
                kwargs = {}
                for i, val in enumerate(args[1:]):
                    if val is not None:
                        kwargs[self.arg_names()[i + 1]] = val
                if len(beams) < 2:
                    self.AddRuntimeMessage(
                        Warning, "At least two beams are required to create a joint."
                    )
                    return
                Rule = DirectRule(self.joint_type, beams, **kwargs)
            return Rule

    def arg_names(self):
        return inspect.getargspec(self.joint_type.__init__)[0][1:]

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
