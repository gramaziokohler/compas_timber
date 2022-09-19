__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.ghpython import list_input_valid, item_input_valid

import Grasshopper.Kernel as ghk
remark = ghk.GH_RuntimeMessageLevel.Remark


Beams = []
if item_input_valid(ghenv, BeamsCollection, "BeamsCollection") and item_input_valid(ghenv, AttrName, "AttrName") and list_input_valid(ghenv, AttrValue, "AttrValue"):
    if AttrName == "category":
        Beams = [b for b in BeamsCollection.objs if b.attributes[AttrName] in [str(x) for x in AttrValue]]
    if AttrName == "width":
        Beams = [b for b in BeamsCollection.objs if b.width in [float(x) for x in AttrValue]]
    if AttrName == "height":
        Beams = [b for b in BeamsCollection.objs if b.height in [float(x) for x in AttrValue]]
    if AttrName == "zaxis":
        ghenv.Component.AddRuntimeMessage(remark, "Given Attribute Name is invalid (accepts only 'category', 'wdth' and 'height')")