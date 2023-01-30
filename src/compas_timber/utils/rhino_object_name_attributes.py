# =======================================================================================
# RHINO-SPECIFIC METHODS
# =======================================================================================

try:
    import Rhino
except Exception:
    pass


def get_rhobj(guid):
    """
    guid: a GUID object, not string
    """
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    return obj


def get_rhobj_name(guid):
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    current_name = obj.Attributes.Name
    return current_name


def set_rhobj_name(guid, new_name):
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    obj.Attributes.Name = new_name
    obj.CommitChanges()
    return


def update_rhobj_attributes_name(guid, attribute, value, separator_entry="_", separator_keyval=":"):
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)

    current_name = obj.Attributes.Name
    # print("current name:",current_name)
    new_name = update_attribute(current_name or "", str(attribute), str(value), separator_entry, separator_keyval)
    # print("new name:",new_name)
    obj.Attributes.Name = new_name
    obj.CommitChanges()


def get_obj_attributes(guid, separator_entry="_", separator_keyval=":"):
    name = get_rhobj_name(guid)
    if name:
        return get_dict_from_str(name, separator_entry="_", separator_keyval=":")
    else:
        return None


# =======================================================================================
# GENERIC PYTHON-ONLY METHODS
# =======================================================================================


def update_attribute(name_str, attr, val, separator_entry="_", separator_keyval=":"):
    if name_str == "":
        d = {}
    else:
        d = get_dict_from_str(name_str, separator_entry, separator_keyval)
    d[attr] = val  # if attr key exists, will be overwritten
    return get_str_from_dict(d, separator_entry, separator_keyval)


def remove_attribute(name_str, attr, separator_entry="_", separator_keyval=":"):
    if name_str == "":
        return name_str
    else:
        d = get_dict_from_str(name_str, separator_entry, separator_keyval)
        if attr in d:
            del d[attr]
        else:
            pass
    return get_str_from_dict(d, separator_entry, separator_keyval)


def get_str_from_dict(name_dict, separator_entry="_", separator_keyval=":"):
    """
    Generates a string by encoding key:value pairs with given separators.
    """
    name_str = ""

    keys = list(name_dict.keys())
    keys.sort()
    for key in keys:
        value = name_dict[key]
        name_str += separator_entry + str(key) + separator_keyval + str(value)

    if name_str[0] == separator_entry:
        name_str = name_str[1:]
    return name_str


def get_dict_from_str(name_str, separator_entry="_", separator_keyval=":"):
    """
    Generates a dictionary from a string of key:value pairs encoded with given separators.
    """
    # name_str = cast_str(name_str)

    data = name_str.split(separator_entry)
    dic = {}
    if len(data) > 0:
        for d in data:
            a = d.split(separator_keyval)
            if len(a) == 2:
                key, value = a
                dic[key] = value

    return dic  # cast_dict(dic)


def cast_dict(dic):
    """
    Checks if dic values are strings maade of allowed chars only.
    """
    for k, v in dic.items():
        # k = cast_str(k)
        # v = cast_str(v)
        dic[k] = v
    return dic


def cast_str(s):
    """
    Checks if string s consists solely of the allowed chars.
    """
    allowed_chars = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_- /;")
    # Check if integer
    # if s.isdigit(): return int(s)
    # Check if set is string
    if set(s).issubset(allowed_chars):
        return s
    # filter for arrays and floats
    try:
        return s  # eval(s)
    except Exception:
        x = [_ for _ in set(s) if _ not in allowed_chars]
        raise Exception("The string contains forbidden characters: %s" % x)


if __name__ == "__main__":

    n1 = "color:blue_shape:triangle"
    print(n1)
    n2 = update_attribute(n1, "color", "grey")
    print(n2)
    n3 = update_attribute(n2, "size", "big")
    print(n3)
    n4 = remove_attribute(n3, "shape")
    print(n4)
