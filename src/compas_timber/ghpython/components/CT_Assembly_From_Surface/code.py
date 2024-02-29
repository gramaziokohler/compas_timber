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
        sheeting_outside,
        sheeting_inside,
        lintel_posts,
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

        if sheeting_outside is not None and not isinstance(sheeting_outside, float):
            raise TypeError("sheeting_outside expected a float, got: {}".format(type(sheeting_outside)))
        if sheeting_inside is not None and not isinstance(sheeting_inside, float):
            raise TypeError("sheeting_inside expected a float, got: {}".format(type(sheeting_inside)))
        if lintel_posts is not None and not isinstance(lintel_posts, bool):
            raise TypeError("lintel_posts expected a bool, got: {}".format(type(lintel_posts)))

        if not ((beam_width and frame_depth) or custom_dimensions):
            raise ValueError(
                "beam_width and frame_depth must be specified either directly or through custom_dimensions."
            )

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None
        if not sheeting_outside:
            sheeting_outside = None
        if not sheeting_inside:
            sheeting_inside = None
        if not lintel_posts:
            lintel_posts = None

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
