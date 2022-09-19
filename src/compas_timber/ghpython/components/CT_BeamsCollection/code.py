__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

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