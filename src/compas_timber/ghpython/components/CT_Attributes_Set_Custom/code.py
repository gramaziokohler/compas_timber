from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Attributes_Set_Custom(component):
    def RunScript(self, ref_obj, attribute, update):
        o = list_input_valid(self, ref_obj, "RefObj")
        a = list_input_valid(self, attribute, "Attribute")

        if update and o and a:
            for attr in attribute:
                if attr:
                    for guid in ref_obj:
                        if guid:
                            update_rhobj_attributes_name(guid, attr.name, attr.value)

        return
