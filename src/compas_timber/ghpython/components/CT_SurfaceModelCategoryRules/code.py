"""Creates a Beam from a LineCurve."""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from scriptcontext import sticky

from Rhino.Geometry import Vector3d as RhinoVector



class SurfaceAssemblyDefaultsComponent(component):
    def RunScript(self, stud_spacing, beam_width, frame_depth, z_axis, options, category):
        if not stud_spacing:
            stud_spacing = 625.0
            self.AddRuntimeMessage(Warning, "default stud spacing 625.0 used")
        if not beam_width:
            beam_width = 60.0
            self.AddRuntimeMessage(Warning, "default beam_width 60.0 used")
        if not frame_depth:
            frame_depth = 200.0
            self.AddRuntimeMessage(Warning, "default frame_depth 200.0 used")
        if z_axis is not None and not isinstance(z_axis, RhinoVector):
            raise TypeError("Expected a compas.geometry.Vector, got: {}".format(type(z_axis)))
        if not z_axis:
            z_axis = RhinoVector(0, 0, 1)
            self.AddRuntimeMessage(Warning, "default z_axis used")

        if not options:
            options = {}

        category_dict = {
            "stud_spacing": stud_spacing,
            "beam_width": beam_width,
            "frame_depth": frame_depth,
            "z_axis": z_axis,
            "options": options,
            "component_guid": self.ComponentGuid
        }

        if not category:
            category = "default"

        sticky_dict = sticky.get("surface_assembly_defaults", None)
        if sticky_dict:
            if sticky_dict.get(category, None) and sticky_dict[category]["component_guid"] == self.ComponentGuid:
                raise ValueError("Category already defined in another component. Please use a different category name.")
            else:
                sticky_dict[category] = category_dict

        else:
            sticky.Add("surface_assembly_defaults", sticky_dict)

        return
