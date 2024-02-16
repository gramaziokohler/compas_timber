from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.ghpython import CategoryRule


def add_param(name, io):
    assert io in ("Output", "Input")
    params = [param.NickName for param in getattr(ghenv.Component.Params, io)]
    if name not in params:
        param = Grasshopper.Kernel.Parameters.Param_GenericObject()
        param.NickName = name + " category"
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.item
        param.Optional = True
        index = getattr(ghenv.Component.Params, io).Count
        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[io])(param, index)
        ghenv.Component.Params.OnParametersChanged()

def clear_params():
    while len(ghenv.Component.Params.Input) > 1:
        ghenv.Component.Params.UnregisterInputParameter(
            ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1]
        )
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(False)


class DirectJointRule(component):
    def RunScript(self, joint_options, *args):
        if not joint_options:  # if no joint_options is input
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
        if register_params:  # if joint_options changes
            if len(joint_options.beam_names) != 2:
                self.AddRuntimeMessage(Error, "Component currently only supports joint types with 2 beams.")
            clear_params()
            for name in joint_options.beam_names:
                add_param(name, "Input")

        if len(ghenv.Component.Params.Input) != len(joint_options.beam_names) + 1 or len(args) != len(
            joint_options.beam_names
        ):  # something went wrong and the number of input parameters is wrong
            self.AddRuntimeMessage(Warning, "Input parameter error.")
            return

        create_rule = True
        for i in range(len(joint_options.beam_names)):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning,
                    "Input parameter {} {} failed to collect data.".format(joint_options.beam_names[i], "categories"),
                )
                create_rule = False
        if create_rule:
            return CategoryRule(joint_options.type, *args, **joint_options.kwargs)
