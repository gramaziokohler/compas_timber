from compas_timber.ghpython.workflow import CategoryRule
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from scriptcontext import sticky
from Rhino.Geometry import Brep as RhinoBrep
from Rhino.Geometry import Vector3d as RhinoVector

from compas.scene import Scene
from compas.geometry import Brep
from compas_timber.assembly.assembly_from_surface import SurfaceAssembly
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
            vals =  sticky.get("surface_assembly_defaults", None)
            if vals:
                stud_spacing = vals.get("stud_spacing", None)
            if not stud_spacing:
                self.AddRuntimeMessage(Warning, "stud_spacing failed to collect data")
        if not isinstance(stud_spacing, float):
            raise TypeError("stud_spacing expected a float, got: {}".format(type(stud_spacing)))

        if not beam_width:
            vals =  sticky.get("surface_assembly_defaults", None)
            if vals:
                beam_width = vals.get("beam_width", None)
            if not beam_width:
                self.AddRuntimeMessage(Warning, "beam_width failed to collect data")
        if not isinstance(beam_width, float):
            raise TypeError("beam_width expected a float, got: {}".format(type(beam_width)))

        if not frame_depth:
            vals =  sticky.get("surface_assembly_defaults", None)
            if vals:
                frame_depth = vals.get("frame_depth", None)
            if not frame_depth:
                self.AddRuntimeMessage(Warning, "frame_depth failed to collect data")
        if not isinstance(frame_depth, float):
            raise TypeError("frame_depth expected a float, got: {}".format(type(frame_depth)))

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None
        default_vals =  sticky.get("surface_assembly_defaults", None).copy()
        default_options = default_vals.get("options", {})


        if default_options:
            if not options:
                options = default_options
            else:
                for key, value in default_options.items():
                    if options.get(key, None) is None:
                        options[key] = value
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            if options[key].get(k) is None:
                                options[key][k] = v
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, CategoryRule):
                                sets = [set(rule.category_a, rule.category_b) for rule in options[key]]
                                if set(v.category_a, v.category_b) not in sets:
                                    options[key].append(v)

        print(options)

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
