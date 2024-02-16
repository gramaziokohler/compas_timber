from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import DirectRule
from compas_timber.ghpython import manage_dynamic_params


class DirectJointRule(component):
    def RunScript(self, joint_options, *args):

        manage_dynamic_params(joint_options.beam_names)

        if len(args) != len(joint_options.beam_names):  # check that dynamic params are correct
            self.AddRuntimeMessage(Error, "Input parameter error.")

        beams = []
        create_rule = True
        for i in range(len(joint_options.beam_names)):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} failed to collect data.".format(joint_options.beam_names[i])
                )
                create_rule = False
            else:
                if not isinstance(args[i], list):
                    args[i] = [args[i]]
                beams.append(args[i])

        if create_rule:
            if len(beams[0]) != len(beams[1]):
                self.AddRuntimeMessage(
                    Error,
                    "Number of items in {} and {} must match!".format(
                        joint_options.beam_names[0], joint_options.beam_names[1]
                    ),
                )
                return
            rules = []
            for main, secondary in zip(beams[0], beams[1]):
                topology, _, _ = ConnectionSolver().find_topology(main, secondary)
                if topology != joint_options.type.SUPPORTED_TOPOLOGY:
                    self.AddRuntimeMessage(
                        Warning,
                        "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                            JointTopology.get_name(topology), joint_options.type.__name__
                        ),
                    )
                    continue
                rules.append(DirectRule(joint_options.type, [main, secondary], **joint_options.kwargs))
            return rules
