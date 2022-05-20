
def are_objects_identical(object1, object2, attributes_to_compare):
    """
    Generic method to check if objects are practically identical
    """

    if type(object1) != type(object2):
        return False

    def _get_val(obj, attr_name):

        #if attr_name in obj.__dir__:
        attrobj = getattr(obj.__class__, attr_name) #TODO: does not find defined attributes, only properties - why?
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