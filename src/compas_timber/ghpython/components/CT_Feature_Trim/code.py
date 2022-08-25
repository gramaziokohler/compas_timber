
from compas_timber.utils.workflow import FeatureDefinition
import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

if not Beam:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Beam failed to collect data")
if not Pln:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Pln failed to collect data")
    
if Beam and Pln:
    Ft = [FeatureDefinition('trim', p, b) for b in Beam for p in Pln]
