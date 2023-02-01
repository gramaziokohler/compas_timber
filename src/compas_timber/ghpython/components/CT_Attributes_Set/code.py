"""Set attributes to the referenced object by encoding them in the objects's name."""

import rhinoscriptsyntax as rs
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.utils.ghpython import list_input_valid
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name


class MyComponent(component):
    def RunScript(self, RefObj, ZVector, Width, Height, Category, update):

        _o = list_input_valid(ghenv, RefObj, "RefObj")
        if not _o:
            return

        # requires at least one of these inputs to be not None
        if ZVector or Width or Height or Category:
            pass
        else:
            ghenv.Component.AddRuntimeMessage(
                Warning, "None of the input parameters 'ZVector', 'Width', 'Height', 'Category' collected any data."
            )

        n = len(RefObj)

        if ZVector:
            if len(ZVector) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Error,
                    " Input parameter 'ZVector' requires either none, one or the same number of values as in refObj.",
                )
        if Width:
            if len(Width) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Error,
                    " Input parameter 'Width' requires either none, one or the same number of values as in refObj.",
                )
        if Height:
            if len(Height) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Error,
                    " Input parameter 'Height' requires either none, one or the same number of values as in refObj.",
                )
        if Category:
            if len(Category) not in (0, 1, n):
                ghenv.Component.AddRuntimeMessage(
                    Error,
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
            for i, ro in enumerate(RefObj):
                guid = ro

                # note: with input type set to Vector, it accepts only a Vector3d, or a string {x,y,z} and casts it to Vector3d
                z = get_item(ZVector, i)
                if z:
                    update_rhobj_attributes_name(guid, "zvector", "{%s,%s,%s}" % (z.X, z.Y, z.Z))

                w = get_item(Width, i)
                if w:
                    update_rhobj_attributes_name(guid, "width", str(w))

                h = get_item(Height, i)
                if h:
                    update_rhobj_attributes_name(guid, "height", str(h))

                c = get_item(Category, i)
                if c:
                    update_rhobj_attributes_name(guid, "category", str(c))

        return
