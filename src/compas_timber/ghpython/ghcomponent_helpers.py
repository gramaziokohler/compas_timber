try:
    import Grasshopper
    from Grasshopper.Kernel.GH_RuntimeMessageLevel import Remark
    from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
    import RhinoCodePluginGH.Parameters;
except (ImportError, SyntaxError):
    pass


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


def get_leaf_subclasses(cls):
    subclasses = []
    for subclass in cls.__subclasses__():
        if not get_leaf_subclasses(subclass):
            subclasses.append(subclass)
        subclasses.extend(get_leaf_subclasses(subclass))
    return subclasses


def add_gh_param(
    name, io, ghenv, index=None
):  # we could also make beam_names a dict with more info e.g. NickName, Description, Access, hints, etc. this would be defined in joint_options components
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
        if not index:
            index = getattr(ghenv.Component.Params, io).Count

        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[io])(param, index)
        ghenv.Component.Params.OnParametersChanged()


def clear_gh_params(ghenv, permanent_param_count=1):
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
        ghenv.Component.Params.UnregisterInputParameter(ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1], True)
        changed = True
    ghenv.Component.Params.OnParametersChanged()
    return changed


def rename_gh_input(input_name, index, ghenv):
    """Renames a parameter in the Grasshopper component.

    Parameters
    ----------
    ghenv : object
        The Grasshopper environment object.
    input_name : str
        The new name of the parameter.
    index : int
        The index of the parameter to rename.

    Returns
    -------
    None

    """
    param = ghenv.Component.Params.Input[index]
    param.NickName = input_name
    param.Name = input_name
    param.Description = input_name
    ghenv.Component.Params.OnParametersChanged()


def rename_gh_output(output_name, index, ghenv):
    """Renames a parameter in the Grasshopper component.

    Parameters
    ----------
    output_name : str
        The new name of the parameter.
    index : int
        The index of the parameter to rename.
    ghenv : object
        The Grasshopper environment object.

    Returns
    -------
    None

    """
    param = ghenv.Component.Params.Output[index]
    param.NickName = output_name
    param.Name = output_name
    param.Description = output_name
    ghenv.Component.Params.OnParametersChanged()


def manage_dynamic_params(input_names, ghenv, rename_count=0, permanent_param_count=0, keep_connections=True):
    """Clears all input parameters from the component.

    Parameters
    ----------
    input_names : list(str)
        The names of the input parameters.
    ghenv : object
        The Grasshopper environment object.
    rename_count : int, optional
        The number of parameters that should be renamed. Default is 0.
    permanent_param_count : int, optional
        The number of parameters that should not be deleted. Default is 0.

    Returns
    -------
    None

    """
    if not input_names:  # if no names are input
        clear_gh_params(ghenv, permanent_param_count)
        return
    else:
        if keep_connections:
            to_remove = []
            for param in ghenv.Component.Params.Input[permanent_param_count + rename_count :]:
                if param.Name not in input_names:
                    to_remove.append(param)
            for param in to_remove:
                param.IsolateObject()
                ghenv.Component.Params.UnregisterInputParameter(param, True)
            for i, name in enumerate(input_names):
                if i < rename_count:
                    rename_gh_input(name, i + permanent_param_count, ghenv)
                elif name not in [param.Name for param in ghenv.Component.Params.Input]:
                    add_gh_param(name, "Input", ghenv, index=i + permanent_param_count)

        else:
            register_params = False
            if len(ghenv.Component.Params.Input) == len(input_names) + permanent_param_count:  # if param count matches beam_names count
                for i, name in enumerate(input_names):
                    if ghenv.Component.Params.Input[i + permanent_param_count].Name != name:  # if param names don't match
                        register_params = True
                        break
            else:
                register_params = True
            if register_params:
                clear_gh_params(ghenv, permanent_param_count + rename_count)  # we could consider renaming params if we don't want to disconnect GH component inputs
                for i, name in enumerate(input_names):
                    if i < permanent_param_count:
                        continue
                    elif i < rename_count:
                        rename_gh_input(name, i, ghenv)
                    else:
                        add_gh_param(name, "Input", ghenv)



def add_cpython_gh_param(
    name, io, ghenv, index=None
):  # we could also make beam_names a dict with more info e.g. NickName, Description, Access, hints, etc. this would be defined in joint_options components
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
        param = RhinoCodePluginGH.Parameters.ScriptVariableParam()
        param.NickName = name
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.item
        param.Optional = True
        if not index:
            index = getattr(ghenv.Component.Params, io).Count

        registers = dict(Input="RegisterInputParam", Output="RegisterOutputParam")
        getattr(ghenv.Component.Params, registers[io])(param, index)
        ghenv.Component.VariableParameterMaintenance()
        ghenv.Component.Params.OnParametersChanged()

def clear_cpython_gh_params(ghenv, permanent_param_count=1):
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
        ghenv.Component.Params.UnregisterInputParameter(ghenv.Component.Params.Input[len(ghenv.Component.Params.Input) - 1], True)
        changed = True
    ghenv.Component.VariableParameterMaintenance()
    ghenv.Component.Params.OnParametersChanged()
    return changed


def rename_cpython_gh_input(input_name, index, ghenv):
    """Renames a parameter in the Grasshopper component.

    Parameters
    ----------
    ghenv : object
        The Grasshopper environment object.
    input_name : str
        The new name of the parameter.
    index : int
        The index of the parameter to rename.

    Returns
    -------
    None

    """
    param = ghenv.Component.Params.Input[index]
    param.NickName = input_name
    param.Name = input_name
    param.Description = input_name
    ghenv.Component.VariableParameterMaintenance()
    ghenv.Component.Params.OnParametersChanged()

def rename_cpython_gh_output(output_name, index, ghenv):
    """Renames a parameter in the Grasshopper component.

    Parameters
    ----------
    output_name : str
        The new name of the parameter.
    index : int
        The index of the parameter to rename.
    ghenv : object
        The Grasshopper environment object.

    Returns
    -------
    None

    """
    param = ghenv.Component.Params.Output[index]
    param.NickName = output_name
    param.Name = output_name
    param.Description = output_name
    ghenv.Component.VariableParameterMaintenance()
    ghenv.Component.Params.OnParametersChanged()

def manage_cpython_dynamic_params(input_names, ghenv, rename_count=0, permanent_param_count=0, keep_connections=True):
    """Clears all input parameters from the component.

    Parameters
    ----------
    input_names : list(str)
        The names of the input parameters.
    ghenv : object
        The Grasshopper environment object.
    rename_count : int, optional
        The number of parameters that should be renamed. Default is 0.
    permanent_param_count : int, optional
        The number of parameters that should not be deleted. Default is 0.

    Returns
    -------
    None

    """
    if not input_names:  # if no names are input
        clear_cpython_gh_params(ghenv, permanent_param_count)
        return
    else:
        if keep_connections:
            to_remove = []
            for param in ghenv.Component.Params.Input[permanent_param_count + rename_count :]:
                if param.Name not in input_names:
                    to_remove.append(param)
            for param in to_remove:
                param.IsolateObject()
                ghenv.Component.Params.UnregisterInputParameter(param, True)
            for i, name in enumerate(input_names):
                if i < rename_count:
                    rename_cpython_gh_input(name, i + permanent_param_count, ghenv)
                elif name not in [param.Name for param in ghenv.Component.Params.Input]:
                    add_cpython_gh_param(name, "Input", ghenv, index=i + permanent_param_count)

        else:
            register_params = False
            if len(ghenv.Component.Params.Input) == len(input_names) + permanent_param_count:  # if param count matches beam_names count
                for i, name in enumerate(input_names):
                    if ghenv.Component.Params.Input[i + permanent_param_count].Name != name:  # if param names don't match
                        register_params = True
                        break
            else:
                register_params = True
            if register_params:
                clear_cpython_gh_params(ghenv, permanent_param_count + rename_count)  # we could consider renaming params if we don't want to disconnect GH component inputs
                for i, name in enumerate(input_names):
                    if i < permanent_param_count:
                        continue
                    elif i < rename_count:
                        rename_cpython_gh_input(name, i, ghenv)
                    else:
                        add_cpython_gh_param(name, "Input", ghenv)
