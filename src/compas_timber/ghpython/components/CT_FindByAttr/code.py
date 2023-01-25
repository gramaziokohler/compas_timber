# flake8: noqa
from compas_timber.utils.ghpython import list_input_valid, item_input_valid

Beams = []
if (
    item_input_valid(ghenv, BeamsCollection, "BeamsCollection")
    and item_input_valid(ghenv, AttrName, "AttrName")
    and list_input_valid(ghenv, AttrValue, "AttrValue")
):
    Beams = [b for b in BeamsCollection.objs if b.attributes[AttrName] in AttrValue]
