"""Read attributes encoded in the referenced object's name."""
import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Remark
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.utils.rhino_object_name_attributes import get_obj_attributes


class MyComponent(component):
    def RunScript(self, refCrv):

        if not refCrv:
            ghenv.Component.AddRuntimeMessage(Warning, "Input parameter refCrv failed to collect data")

        ZVector = []
        Width = []
        Height = []
        Category = []
        Group = []

        guid = refCrv
        if guid:
            # get attributes from the name string ==========================================
            attr = get_obj_attributes(guid)
            if attr:
                if "width" in attr:
                    Width = float(attr["width"])
                if "height" in attr:
                    Height = float(attr["height"])
                if "category" in attr:
                    Category = attr["category"]
                if "zvector" in attr:
                    ZVector = attr["zvector"]
                    # it's a string, but Grasshopper will automatically cast this input as Vector3d

            # get the group if objects are grouped =========================================
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
            attr = obj.Attributes
            gl = attr.GetGroupList()  # group indices
            if gl:
                gl = list(gl)
                if len(gl) > 1:
                    ghenv.Component.AddRuntimeMessage(
                        Remark, "Some objects belong to more than one group! (I will pick the first group I find.)"
                    )
                Group = gl[0]

            else:
                Group = []

        return (ZVector, Width, Height, Category, Group)
