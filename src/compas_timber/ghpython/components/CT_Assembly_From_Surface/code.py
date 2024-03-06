"""Creates a Beam from a LineCurve."""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.Geometry import Brep as RhinoBrep
from Rhino.Geometry import Vector3d as RhinoVector
from compas.scene import Scene
from compas.geometry import Brep
from compas_timber.assembly import SurfaceAssembly


class Assembly_From_Surface(component):
    def RunScript(
        self,
        surface,
        stud_spacing,
        beam_width,
        frame_depth,
        z_axis,
        custom_dimensions,
    ):
        # minimum inputs required
        if not surface:
            return
        if not isinstance(surface, RhinoBrep):
            raise TypeError("Expected a compas.geometry.Surface, got: {}".format(type(surface)))
        if not stud_spacing:
            self.AddRuntimeMessage(Warning, "Input parameter 'spacing' failed to collect data")
        if not isinstance(stud_spacing, float):
            raise TypeError("stud_spacing expected a float, got: {}".format(type(stud_spacing)))

        if z_axis is not None and not isinstance(z_axis, RhinoVector):
            raise TypeError("Expected a compas.geometry.Vector, got: {}".format(type(z_axis)))

        if not ((beam_width and frame_depth) or custom_dimensions):
            raise ValueError(
                "beam_width and frame_depth must be specified either directly or through custom_dimensions."
            )

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None

        assembly = SurfaceAssembly(
            Brep.from_native(surface),
            stud_spacing,
            beam_width,
            frame_depth,
            z_axis,
            custom_dimensions=custom_dimensions,
        )

        scene = Scene()
        for beam in assembly.beams:
            scene.add(beam.blank)
        Blanks = scene.draw()
        return assembly.beams, assembly.rules, Blanks
