from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import clr
import System
import inspect
import itertools

from compas_timber.connections import Joint
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology

from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import get_all_subclasses
from compas_timber.ghpython import DirectRule


class DirectJointRule(component):
    def __init__(self):
        super(DirectJointRule, self).__init__()
        self.classes =  {}
        for cls in get_all_subclasses(Joint):
            self.classes[cls.__name__] = cls
        self.items = []
        self.joint_type = None
        self.joint_name = None


    def RunScript(self, *args):
        if not self.joint_type:
            ghenv.Component.Message = "Select joint type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select joint type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.joint_name
            beam_a = args[0]
            beam_b = args[1]
            kwargs = {}
            for i, val in enumerate(args[2:]):
                if val:
                    kwargs[self.arg_names()[i+2]] = val

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
                if topology != self.joint_type.SUPPORTED_TOPOLOGY:
                    self.AddRuntimeMessage(
                        Warning,
                        "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                            JointTopology.get_name(topology), self.joint_type.__name__
                        ),
                    )
                Rules.append(DirectRule(self.joint_type, [secondary, main], **kwargs))
            return Rules


    def arg_names(self):
        return inspect.getargspec(self.joint_type.__init__)[0][1:]

    def AppendAdditionalMenuItems(self, menu):
        if self.items:
            for item in self.items:
                menu.Items.Add(item)
        else:
            for name in self.classes.keys():
                item = menu.Items.Add(name, None, self.on_item_click)
                self.items.append(item)


    def on_item_click(self, sender, event_info):
        active_item = clr.Convert(sender, System.Windows.Forms.ToolStripItem)
        active_item.Checked = True

        for item in self.items:
            if str(item) != str(sender):
                item.Checked = False

        self.joint_name = str(sender)

        self.joint_type = self.classes[self.joint_name]


        manage_dynamic_params(self.arg_names(), ghenv, rename_count = 2, permanent_param_count = 0)

        ghenv.Component.ExpireSolution(True)
