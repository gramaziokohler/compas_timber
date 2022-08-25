"""Creates a Collection of Beams."""
from compas_timber.utils.workflow import CollectionDef
import Grasshopper.Kernel as ghk
warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error
remark = ghk.GH_RuntimeMessageLevel.Remark

from compas_timber.utils.ghpython import list_input_valid


if list_input_valid(ghenv, Beams, "Beams"):

    #check for duplicate beams (using hash) TODO: revise hash input
    if len(set(Beams)) != len(Beams): 
        ghenv.Component.AddRuntimeMessage(error, "There are beams that look duplicate/identical. Check your inputs.")

    BeamsCollection = CollectionDef(Beams)