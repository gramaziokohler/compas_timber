from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.ghpython import CategoryRule


def AddParam(name, IO):
    assert IO in ("Output", "Input")
    params = [param.NickName for param in getattr(ghenv.Component.Params, IO)]
    if name not in params:
        param = Grasshopper.Kernel.Parameters.Param_GenericObject()
        param.NickName = name + " category"
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.item
        param.Optional = True
        index = getattr(ghenv.Component.Params, IO).Count
        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[IO])(param, index)
        ghenv.Component.Params.OnParametersChanged()

def ClearParams():
    while len(ghenv.Component.Params.Input) > 1:
        ghenv.Component.Params.UnregisterInputParameter(
            ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1]
        )
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(False)


class DirectJointRule(component):
    def RunScript(self, JointOptions, *args):
        if not JointOptions:  # if no JointOptions is input
            ClearParams()
            return

        register_params = False
        if len(ghenv.Component.Params.Input) == len(JointOptions.beam_names) + 1:
            for i, name in enumerate(JointOptions.beam_names):
                if ghenv.Component.Params.Input[i + 1].Name != name:
                    register_params = True
                    break
        else:
            register_params = True
        if register_params:  # if JointOptions changes
            if len(JointOptions.beam_names) != 2:
                self.AddRuntimeMessage(Error, "Component currently only supports joint types with 2 beams.")
            ClearParams()
            for name in JointOptions.beam_names:
                AddParam(name, "Input")

        if len(ghenv.Component.Params.Input) != len(JointOptions.beam_names) + 1 or len(args) != len(
            JointOptions.beam_names
        ):  # something went wrong and the number of input parameters is wrong
            self.AddRuntimeMessage(Warning, "Input parameter error.")
            return

        create_rule = True
        for i in range(len(JointOptions.beam_names)):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning,
                    "Input parameter {} {} failed to collect data.".format(JointOptions.beam_names[i], "categories"),
                )
                create_rule = False
        if create_rule:
            return CategoryRule(JointOptions.type, *args, **JointOptions.kwargs)
