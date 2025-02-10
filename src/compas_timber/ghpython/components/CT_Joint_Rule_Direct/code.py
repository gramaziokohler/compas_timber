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


class DirectJointRule(component):
    def __init__(self):
        super(DirectJointRule, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(Joint):
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
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val is not None:
                    kwargs[self.arg_names()[i + 2]] = val

            if not beam_a:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[0]))
            if not beam_b:
                self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data.".format(self.arg_names()[1]))
            if not (args[0] and args[1]):
                return
            if not isinstance(beam_a, list):
                beam_a = [beam_a]
            if not isinstance(beam_b, list):
                beam_b = [beam_b]
            if len(beam_a) != len(beam_b):
                self.AddRuntimeMessage(Error, "Number of items in {} and {} must match!".format(self.arg_names()[0], self.arg_names()[1]))
                return
            Rules = []
            for main, secondary in zip(beam_a, beam_b):
                topology, _, _ = ConnectionSolver().find_topology(main, secondary)
                supported_topo = self.joint_type.SUPPORTED_TOPOLOGY
                if not isinstance(supported_topo, list):
                    supported_topo = [supported_topo]
                if topology not in supported_topo:
                    self.AddRuntimeMessage(
                        Warning,
                        "Beams meet with topology: {} which does not agree with joint of type: {}".format(JointTopology.get_name(topology), self.joint_type.__name__),
                    )
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
        rename_gh_output(self.joint_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=2, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
