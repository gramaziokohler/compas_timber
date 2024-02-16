from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import DirectRule


def add_param(name, IO):
    assert IO in ("Output", "Input")
    params = [param.NickName for param in getattr(ghenv.Component.Params, IO)]
    if name not in params:
        param = Grasshopper.Kernel.Parameters.Param_GenericObject()
        param.NickName = name
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.list
        param.Optional = True
        index = getattr(ghenv.Component.Params, IO).Count
        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[IO])(param, index)
        ghenv.Component.Params.OnParametersChanged()

def clear_params():
    while len(ghenv.Component.Params.Input) > 1:
        ghenv.Component.Params.UnregisterInputParameter(
            ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1]
        )
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(True)


class DirectJointRule(component):
    def RunScript(self, joint_options, *args):
        if not joint_options:  # if no JointOptions is input
            clear_params()
            return

        register_params = False
        if len(ghenv.Component.Params.Input) == len(joint_options.beam_names) + 1:
            for i, name in enumerate(joint_options.beam_names):
                if ghenv.Component.Params.Input[i + 1].Name != name:
                    register_params = True
                    break
        else:
            register_params = True
        if register_params:  # if JointOptions changes
            if len(joint_options.beam_names) != 2:
                self.AddRuntimeMessage(Error, "Component currently only supports joint types with 2 beams.")
            clear_params()
            for name in joint_options.beam_names:
                add_param(name, "Input")

        if (
            len(ghenv.Component.Params.Input) != len(joint_options.beam_names) + 1
        ):  # something went wrong and the number of input parameters is wrong
            self.AddRuntimeMessage(Warning, "Input parameter error.")
            return

        beams = []
        create_rule = True
        for i in range(len(ghenv.Component.Params.Input) - 1):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} failed to collect data.".format(joint_options.beam_names[i])
                )
                create_rule = False
            else:
                arg_beams = args[i]
                if not isinstance(arg_beams, list):
                    arg_beams = [arg_beams]
                beams.append(arg_beams)

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
