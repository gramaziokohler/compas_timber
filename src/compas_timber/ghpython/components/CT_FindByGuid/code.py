def find_part_with_rhino_id(parts, guid):
    for g in guid:
        for part in parts:
            if part.attributes.get("rhino_guid", None) == g:
                return part


if Collection and refObj:
    Obj = find_part_with_rhino_id(Collection.objs, refObj)