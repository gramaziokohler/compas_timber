__author__ = "aapolina"
__version__ = "2022.08.16"


import Rhino
from compas_timber.utils.rhino_object_name_attributes import get_obj_attributes

guid = refObj

if guid:

    # get attributes from the name string ==========================================
    attr = get_obj_attributes(guid)
    if attr:
        if 'width' in attr: W = float(attr['width']) 
        if 'height' in attr: H = float(attr['height'])
        if 'category' in attr: Cat = attr['category']
        if 'zaxis' in attr: 
            ZVec = attr['zaxis']

    # get the group if objects are grouped =========================================
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    attr = obj.Attributes
    gl = attr.GetGroupList() #group indices
    if gl: 
        gl = list(gl)
        if len(gl)>1: 
            print("This object () belongs to more than one group! (I will pick the first group I find.)")
        group = gl[0]
    else:
        group = None


    Gr = group