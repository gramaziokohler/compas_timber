from Grasshopper.Kernel.GH_RuntimeMessageLevel import Remark
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper


def list_input_valid(component, Param, name):
    if not Param:
        component.AddRuntimeMessage(Warning, "Input parameter %s failed to collect data" % name)
    else:
        if all([_ is None for _ in Param]):
            component.AddRuntimeMessage(Warning, "Input parameter %s failed to collect data" % name)
        elif any([_ is None for _ in Param]):
            component.AddRuntimeMessage(Remark, "Input parameter %s contains some Null values" % name)
            return True
        else:
            return True
    return False


def item_input_valid(component, Param, name):
    if not Param:
        component.AddRuntimeMessage(Warning, "Input parameter %s failed to collect data" % name)
    else:
        return True
    return False


def add_GH_param(name, io, ghenv):
    assert io in ("Output", "Input")
    params = [param.NickName for param in getattr(ghenv.Component.Params, io)]
    if name not in params:
        param = Grasshopper.Kernel.Parameters.Param_GenericObject()
        param.NickName = name
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.item
        param.Optional = True
        index = getattr(ghenv.Component.Params, io).Count
        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[io])(param, index)
        ghenv.Component.Params.OnParametersChanged()


def clear_GH_params(ghenv, permanent_param_count=1):
    while len(ghenv.Component.Params.Input) > permanent_param_count:
        ghenv.Component.Params.UnregisterInputParameter(
            ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1]
        )
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(False)


def manage_dynamic_params(input_names, ghenv, permanent_param_count=1):
    if not input_names:  # if no joint_options is input
        clear_GH_params(ghenv, permanent_param_count)
        return
    register_params = False
    if len(ghenv.Component.Params.Input) == len(input_names) + permanent_param_count:
        for i, name in enumerate(input_names):
            if ghenv.Component.Params.Input[i + permanent_param_count].Name != name:
                register_params = True
                break
    else:
        register_params = True
    if register_params:
        clear_GH_params(ghenv, permanent_param_count)
        for name in input_names:
            add_GH_param(name, "Input", ghenv)
