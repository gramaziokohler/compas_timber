# r: compas_timber>=0.15.3
import Grasshopper
import System

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Attributes_Set_Custom(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, ref_obj: System.Collections.Generic.List[System.Guid], attribute: System.Collections.Generic.List[object], update):
        o = list_input_valid_cpython(ghenv, ref_obj, "RefObj")
        a = list_input_valid_cpython(ghenv, attribute, "Attribute")

        if update and o and a:
            for attr in attribute:
                if attr:
                    for guid in ref_obj:
                        if guid:
                            update_rhobj_attributes_name(guid, attr.name, attr.value)

        return
