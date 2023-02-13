from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_timber.ghpython.ghcomponent_helpers import item_input_valid
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Attributes_Delete(component):
    def RunScript(self, RefObj, AttributeName, update):

        if not item_input_valid(ghenv, RefObj, "RefObj"):
            return

        if update and RefObj:
            if not AttributeName:
                # clear all attributes from the refecenced object's name
                update_rhobj_attributes_name(RefObj, operation="clear")
            else:
                # remove only the indicated attributes
                for attr in AttributeName:
                    update_rhobj_attributes_name(RefObj, attribute=attr, operation="remove")

        return
