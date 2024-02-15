from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import DirectRule


def AddParam(name, IO, list=True):
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
        return param


class DirectJointRule(component):
    def __init__(self):
        self.joint_type = None

    def ClearParams(self):
        while len(ghenv.Component.Params.Input) > 1:
            ghenv.Component.Params.UnregisterInputParameter(
                ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1]
            )
        ghenv.Component.Params.OnParametersChanged()

    def RunScript(self, JointOptions, *args):
        if not JointOptions:  # if no JointOptions is input
            self.ClearParams()
            self.joint_type = None
            return

        if JointOptions.type != self.joint_type:  # if JointOptions changes
            if len(JointOptions.beam_names) != 2:
                self.AddRuntimeMessage(Error, "Component currently only supports joint types with 2 beams.")
            self.ClearParams()
            self.joint_type = JointOptions.type
            for name in JointOptions.beam_names:
                AddParam(name, "Input")

        if len(ghenv.Component.Params.Input) != 3:
            self.AddRuntimeMessage(Warning, "Input parameter error.")
            return

        if len(args) < 2:
            self.AddRuntimeMessage(Warning, "Input parameters failed to collect data.")
            return

        beams = []
        create_rule = True
        for i in range(len(ghenv.Component.Params.Input) - 1):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} failed to collect data.".format(JointOptions.beam_names[i])
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
                        JointOptions.beam_names[0], JointOptions.beam_names[1]
                    ),
                )
                return
            Rules = []
            for main, secondary in zip(beams[0], beams[1]):
                topology, _, _ = ConnectionSolver().find_topology(main, secondary)
                if topology != JointOptions.type.SUPPORTED_TOPOLOGY:
                    self.AddRuntimeMessage(
                        Warning,
                        "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                            JointTopology.get_name(topology), JointOptions.type.__name__
                        ),
                    )
                    continue
                Rules.append(DirectRule(JointOptions.type, [main, secondary], **JointOptions.kwargs))
            return Rules
