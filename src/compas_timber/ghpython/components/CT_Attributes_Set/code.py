from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name

if update:
    for attr in attribute:
        for guid in refObj:
            update_rhobj_attributes_name(guid, attr.name, attr.value)