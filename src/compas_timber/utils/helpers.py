from math import fabs


def close(x, y, tol=1e-12):
    """Shorthand for comparing two numbers or None.

    Returns True if `x` and `y` are equal within the given tolerance.
    Returns True also if both `x` and `y` are None.

    TODO: revise if needed, handling Nones can be the responsibility of the caller.

    Parameters
    ----------
    x : float
        First number.
    y : float
        First number.
    tol : float
        Comparison tolerance.

    Returns
    -------
    bool

    """
    if x is None and y is None:
        return True
    return fabs(x - y) < tol  # same as close() in compas.geometry


def are_objects_identical(object1, object2, attributes_to_compare):
    """Generic method to check if objects are practically identical.

    TODO: revise if needed. this is very generic so might not belong here. comparison like this for value types belong in __eq__ e.g.

    """

    if type(object1) != type(object2):
        return False

    def _get_val(obj, attr_name):
        # if attr_name in obj.__dir__:
        attrobj = getattr(obj.__class__, attr_name)  # TODO: does not find defined attributes, only properties - why?
        if isinstance(attrobj, property):
            val = attrobj.__get__(obj, obj.__class__)
            return val
        else:
            NotImplementedError

    for attr_name in attributes_to_compare:
        val1 = getattr(object1, attr_name)
        val2 = getattr(object2, attr_name)
        if val1 != val2:
            return False

    return True
