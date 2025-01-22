"""Read attributes encoded in the referenced object's name."""

import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Remark
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython.rhino_object_name_attributes import get_obj_attributes


class Attributes_Get(component):
    def RunScript(self, ref_crv):
        if not ref_crv:
            self.AddRuntimeMessage(Warning, "Input parameter RefCrv failed to collect data")

        z_vector = []
        width = []
        height = []
        category = []
        group = []

        guid = ref_crv
        if guid:
            # get attributes from the name string ==========================================
            attr = get_obj_attributes(guid)
            if attr:
                if "width" in attr:
                    width = float(attr["width"])
                if "height" in attr:
                    height = float(attr["height"])
                if "category" in attr:
                    category = attr["category"]
                if "zvector" in attr:
                    z_vector = attr["zvector"]
                    # it's a string, but Grasshopper will automatically cast this input as Vector3d

            # get the group if objects are grouped =========================================
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
            attr = obj.Attributes
            gl = attr.GetGroupList()  # group indices
            if gl:
                gl = list(gl)
                if len(gl) > 1:
                    self.AddRuntimeMessage(Remark, "Some objects belong to more than one group! (I will pick the first group I find.)")
                group = gl[0]

            else:
                group = []

        return (z_vector, width, height, category, group)
