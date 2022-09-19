__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska"]
__license__ = "MIT"
__version__ = "20.09.2022"

import Grasshopper.Kernel as ghk
warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error
remark = ghk.GH_RuntimeMessageLevel.Remark

def list_input_valid(ghenv, Param, name):

    if not Param:
        ghenv.Component.AddRuntimeMessage(warning, "Input parameter %s failed to collect data"%name)
    else:
        if all([_==None for _ in Param]):
            ghenv.Component.AddRuntimeMessage(warning, "Input parameter %s failed to collect data"%name)
        elif any([_==None for _ in Param]):
            ghenv.Component.AddRuntimeMessage(remark, "Input parameter %s contains some Null values"%name)
            return True
        else:
            return True
    return False


def item_input_valid(ghenv, Param, name):

    if not Param:
        ghenv.Component.AddRuntimeMessage(warning, "Input parameter %s failed to collect data"%name)
    else:
            return True
    return False
