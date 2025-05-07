# r: compas_timber>=0.15.3
"""Read all attributes encoded in the referenced object's name."""

# flake8: noqa
import Grasshopper
import System

from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython
from compas_timber.ghpython.rhino_object_name_attributes import get_obj_attributes


class Attributes_Get_Custom(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, ref_crv: System.Guid):
        if not item_input_valid_cpython(ghenv, ref_crv, "RefCrv"):
            return
        AttributeName = []
        AttributeValue = []

        guid = ref_crv
        if guid:
            attrdict = get_obj_attributes(guid)
            if attrdict:
                AttributeName = attrdict.keys()
                AttributeValue = [attrdict[k] for k in AttributeName]

        return (AttributeName, AttributeValue)
