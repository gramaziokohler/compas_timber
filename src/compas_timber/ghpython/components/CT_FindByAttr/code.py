# flake8: noqa
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid

Beams = []
if (
    item_input_valid(ghenv, BeamsCollection, "BeamsCollection")
    and item_input_valid(ghenv, AttrName, "AttrName")
    and list_input_valid(ghenv, AttrValue, "AttrValue")
):
    Beams = [b for b in BeamsCollection.objs if b.attributes[AttrName] in AttrValue]
