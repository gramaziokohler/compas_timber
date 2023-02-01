from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.utils.ghpython import list_input_valid
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name


class MyComponent(component):
    def RunScript(self, RefObj, Attribute, update):

        o = list_input_valid(ghenv, RefObj, "RefObj")
        a = list_input_valid(ghenv, Attribute, "Attribute")

        if update and o and a:
            for attr in Attribute:
                if attr:
                    for guid in RefObj:
                        if guid:
                            update_rhobj_attributes_name(guid, attr.name, attr.value)

        return
