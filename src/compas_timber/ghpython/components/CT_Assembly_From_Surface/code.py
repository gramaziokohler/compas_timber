"""Creates a Beam from a LineCurve."""

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from Rhino.Geometry import Brep as RhinoBrep
from Rhino.Geometry import Vector3d as RhinoVector
from compas.scene import Scene
from compas.geometry import Brep
from compas_timber.assembly import SurfaceAssembly
from compas_timber.ghpython import DebugInfomation
from compas_timber.consumers import BrepGeometryConsumer


class SurfaceAssemblyComponent(component):
    def RunScript(self, surface, stud_spacing, beam_width, frame_depth, z_axis, openings, options, CreateGeometry=False):
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

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None
        if not options:
            options = {}


        assembly = SurfaceAssembly(Brep.from_native(surface), stud_spacing, beam_width, frame_depth, z_axis, openings = openings, **options)

        debug_info = DebugInfomation()
        Geometry = None
        scene = Scene()
        if CreateGeometry:
            vis_consumer = BrepGeometryConsumer(assembly.assembly)
            for result in vis_consumer.result:
                scene.add(result.geometry)
                if result.debug_info:
                    debug_info._has_errors = False
                    for error in result.debug_info:
                        if error.message != "The volume does not intersect with beam geometry.":
                            debug_info.add_feature_error(result.debug_info)
                            debug_info._has_errors = True
        else:
            for beam in assembly.beams:
                scene.add(beam.blank)

        if debug_info.has_errors:
            self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

        Geometry = scene.draw()

        return assembly.assembly, Geometry, debug_info
