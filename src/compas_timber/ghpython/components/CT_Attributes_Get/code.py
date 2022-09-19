__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

import Rhino
from compas_timber.utils.rhino_object_name_attributes import get_obj_attributes

import Grasshopper.Kernel as ghk
warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error
remark = ghk.GH_RuntimeMessageLevel.Remark

if not refCrv:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter refCrv failed to collect data")

guid = refCrv
if guid:
    # get attributes from the name string ==========================================
    attr = get_obj_attributes(guid)
    if attr:
        if 'width' in attr:     Width = float(attr['width']) 
        if 'height' in attr:    Height = float(attr['height'])
        if 'category' in attr:  Category = attr['category']
        if 'zaxis' in attr:     ZVector = attr['zaxis']

    # get the group if objects are grouped =========================================
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    attr = obj.Attributes
    gl = attr.GetGroupList() #group indices
    if gl: 
        gl = list(gl)
        if len(gl)>1: 
            ghenv.Component.AddRuntimeMessage(remark, "Some objects belong to more than one group! (I will pick the first group I find.)")
        Group = gl[0]
        
    else:
        Group = None
