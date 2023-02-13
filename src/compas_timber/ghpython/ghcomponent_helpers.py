from Grasshopper.Kernel.GH_RuntimeMessageLevel import Remark
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


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
