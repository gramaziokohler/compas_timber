from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.ghpython.ghcomponent_helpers import item_input_valid
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Attributes_Delete(component):
    def RunScript(self, ref_obj, attribute_name, update):
        if not item_input_valid(self, ref_obj, "RefObj"):
            return

        if update and ref_obj:
            if not attribute_name:
                # clear all attributes from the refecenced object's name
                update_rhobj_attributes_name(ref_obj, operation="clear")
            else:
                # remove only the indicated attributes
                for attr in attribute_name:
                    update_rhobj_attributes_name(ref_obj, attribute=attr, operation="remove")

        return
