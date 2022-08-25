import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

def find_part_with_rhino_id(parts, guid):
    for g in guid:
        for part in parts:
            if part.attributes.get("rhino_guid", None) == g:
                return part

if not Collection:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Collection failed to collect data")
elif not Collection.objs:
    ghenv.Component.AddRuntimeMessage(warning, "There are no objects in the Collection")

if not refObj:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter refObj failed to collect data")

if Collection and refObj:
    found = find_part_with_rhino_id(Collection.objs, refObj)
    if found: 
        Obj=found
    else:
        ghenv.Component.AddRuntimeMessage(warning, "No objects found")