# r: compas_timber>=0.15.3
"""Set attributes to the referenced object by encoding them in the objects's name."""

# flake8: noqa
import Grasshopper
import Rhino
import System

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Attributes_Set(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self,
        ref_obj: System.Collections.Generic.List[System.Guid],
        z_vector: System.Collections.Generic.List[Rhino.Geometry.Vector3d],
        width: System.Collections.Generic.List[float],
        height: System.Collections.Generic.List[float],
        category: System.Collections.Generic.List[str],
        update: bool,
    ):
        if not list_input_valid_cpython(self, ref_obj, "RefObj"):
            return

        # requires at least one of these inputs to be not None
        if z_vector or width or height or category:
            pass
        else:
            ghenv.Component.AddRuntimeMessage(
                Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "None of the input parameters 'ZVector', 'Width', 'Height', 'Category' collected any data."
            )

        n = len(ref_obj)

        if z_vector:
            if len(z_vector) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    " Input parameter 'ZVector' requires either none, one or the same number of values as in refObj.",
                )
        if width:
            if len(width) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    " Input parameter 'Width' requires either none, one or the same number of values as in refObj.",
                )
        if height:
            if len(height) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    " Input parameter 'Height' requires either none, one or the same number of values as in refObj.",
                )
        if category:
            if len(category) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                    " Input parameter 'Category' requires either none, one or the same number of values as in refObj.",
                )

        def get_item(items, i):
            if not items:
                return None
            if len(items) == 1:
                return items[0]
            else:
                return items[i]

        if update:
            for i, ro in enumerate(ref_obj):
                guid = ro

                # note: with input type set to Vector, it accepts only a Vector3d, or a string {x,y,z} and casts it to Vector3d
                z = get_item(z_vector, i)
                if z:
                    update_rhobj_attributes_name(guid, "zvector", "{%s,%s,%s}" % (z.X, z.Y, z.Z))

                w = get_item(width, i)
                if w:
                    update_rhobj_attributes_name(guid, "width", str(w))

                h = get_item(height, i)
                if h:
                    update_rhobj_attributes_name(guid, "height", str(h))

                c = get_item(category, i)
                if c:
                    update_rhobj_attributes_name(guid, "category", str(c))

        return
