import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

if not Collection:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Collection failed to collect data")
elif not Collection.objs:
    ghenv.Component.AddRuntimeMessage(warning, "There are no objects in the Collection")

if not Index:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Index failed to collect data")

if Collection and Index:
    found = [v for k,v in Collection.keys_map.items() if k in Index]
    if found: 
        Obj=found
    else:
        ghenv.Component.AddRuntimeMessage(warning, "No objects found")