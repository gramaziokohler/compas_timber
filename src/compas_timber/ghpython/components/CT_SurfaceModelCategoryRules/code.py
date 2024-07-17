"""Creates a Beam from a LineCurve."""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
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

        if not category:
            category = "default"

        guid_dict = {
            "stud_spacing": stud_spacing,
            "beam_width": beam_width,
            "frame_depth": frame_depth,
            "z_axis": z_axis,
            "options": options,
            "category": category
        }

        for key, value in sticky["surface_assembly_defaults"].items():
            if key != str(self.InstanceGuid) and value.get("category", None) == category:
                self.AddRuntimeMessage(Error, "category attributes already defined")

        sticky["surface_assembly_defaults"][str(self.InstanceGuid)] = guid_dict

    def __enter__(self):
        if not sticky.get("surface_assembly_defaults", None):
            sticky.Add("surface_assembly_defaults", {})
        sticky["surface_assembly_defaults"][str(self.InstanceGuid)] = {}

    def __exit__(self):
        sticky["surface_assembly_defaults"].pop(str(self.InstanceGuid))
