from compas_timber.utils.workflow import JointDefinition

import Grasshopper.Kernel as ghk

w = ghk.GH_RuntimeMessageLevel.Warning
e = ghk.GH_RuntimeMessageLevel.Error

if not B1:
    ghenv.Component.AddRuntimeMessage(w, "Input parameter B1 failed to collect data")
if not B2:
    ghenv.Component.AddRuntimeMessage(w, "Input parameter B2 failed to collect data")
if (B1 and B2) and (len(B1) != len(B2)):
    ghenv.Component.AddRuntimeMessage(e, " I need an equal number of Beams in B1 and B2")


else:
    TButt = []
    for beam1, beam2 in zip(B1, B2):
        if beam1 and beam2:
            TButt.append(JointDefinition("T-Butt", (beam1, beam2)))
        else:
            ghenv.Component.AddRuntimeMessage(w, "Some of the inputs are Null")
