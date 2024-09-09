"""Read all attributes encoded in the referenced object's name."""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython.rhino_object_name_attributes import get_obj_attributes


class Attributes_Get_Custom(component):
    def RunScript(self, RefCrv):
        if not RefCrv:
            self.AddRuntimeMessage(Warning, "Input parameter RefCrv failed to collect data")

        AttributeName = []
        AttributeValue = []

        guid = RefCrv
        if guid:
            attrdict = get_obj_attributes(guid)
            if attrdict:
                AttributeName = attrdict.keys()
                AttributeValue = [attrdict[k] for k in AttributeName]

        return (AttributeName, AttributeValue)
