"""Creates a Collection of Beams."""
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid
from compas_timber.utils.workflow import CollectionDef

if list_input_valid(ghenv, Beams, "Beams"):

    # check for duplicate beams (using hash) TODO: revise hash input
    if len(set(Beams)) != len(Beams):
        ghenv.Component.AddRuntimeMessage(Error, "There are beams that look duplicate/identical. Check your inputs.")

    BeamsCollection = CollectionDef(Beams)
