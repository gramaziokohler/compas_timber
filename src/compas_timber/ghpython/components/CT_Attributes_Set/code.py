# flake8: noqa
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.utils.ghpython import list_input_valid


o = list_input_valid(ghenv, refObj, "refObj")
a = list_input_valid(ghenv, Attribute, "Attribute")

if update and o and a:
    for attr in Attribute:
        if attr:
            for guid in refObj:
                if guid:
                    update_rhobj_attributes_name(guid, attr.name, attr.value)
