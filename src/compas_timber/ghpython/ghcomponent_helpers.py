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


def add_GH_param(name, io, ghenv):   #we could also make beam_names a dict with more info e.g. NickName, Description, Access, hints, etc. this would be defined in joint_options components
    """Adds a parameter to the Grasshopper component.

    Parameters
    ----------
    name : str
        The name of the parameter.
    io : str
        The direction of the parameter. Either "Input" or "Output".
    ghenv : object
        The Grasshopper environment object.

    Returns
    -------
    None

    """
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
    """Clears all input parameters from the component.

    Parameters
    ----------
    ghenv : object
        The Grasshopper environment object.
    permanent_param_count : int, optional
        The number of parameters that should not be deleted. Default is 1.

    Returns
    -------
    None

    """
    changed = False
    while len(ghenv.Component.Params.Input) > permanent_param_count:
        ghenv.Component.Params.UnregisterInputParameter(
            ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1],
            True
        )
        changed = True
    if changed:
        ghenv.Component.ExpireSolution(True)


def manage_dynamic_params(input_names, ghenv, permanent_param_count=1):
    """Clears all input parameters from the component.

    Parameters
    ----------
    input_names : list(str)
        The names of the input parameters.
    ghenv : object
        The Grasshopper environment object.
    permanent_param_count : int, optional
        The number of parameters that should not be deleted. Default is 1.

    Returns
    -------
    None

    """
    if not input_names:  # if no names are input
        clear_GH_params(ghenv, permanent_param_count)
        return
    else:
        register_params = False
        if len(ghenv.Component.Params.Input) == len(input_names) + permanent_param_count:           #if param count matches beam_names count
            for i, name in enumerate(input_names):
                if ghenv.Component.Params.Input[i + permanent_param_count].Name != name:            #if param names don't match
                    register_params = True
                    break
        else:
            register_params = True
        if register_params:
            clear_GH_params(ghenv, permanent_param_count)       #we could consider renaming params if we don't want to disconnect GH component inputs
            for name in input_names:
                add_GH_param(name, "Input", ghenv)
            ghenv.Component.ExpireSolution(True)

