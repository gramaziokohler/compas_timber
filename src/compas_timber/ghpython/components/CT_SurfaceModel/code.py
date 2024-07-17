"""Creates a Beam from a LineCurve."""

from compas.geometry import Brep
from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.Geometry import Brep as RhinoBrep
from scriptcontext import sticky

from compas_timber.design import DebugInfomation
from compas_timber.design import SurfaceModel
from compas_timber.design import CategoryRule


class SurfaceModelComponent(component):
    def RunScript(self, surface, stud_spacing, beam_width, frame_depth, z_axis, options, category, CreateGeometry=False):
        # minimum inputs required
        if not surface:
            return
        if not isinstance(surface, RhinoBrep):
            raise TypeError("Expected a compas.geometry.Surface, got: {}".format(type(surface)))
        if not category:
            category = "default"
        defaults = sticky.get("surface_assembly_defaults", None)
        guid = None
        if defaults:
            for key, value in defaults.items():
                if value.get("category", None) == category:
                    guid = key
                    break

        vals = defaults.get(guid, None)
        if not stud_spacing:
            if vals:
                stud_spacing = vals.get("stud_spacing", None)
            if not stud_spacing:
                self.AddRuntimeMessage(Warning, "stud_spacing failed to collect data")
        if not isinstance(stud_spacing, float):
            raise TypeError("stud_spacing expected a float, got: {}".format(type(stud_spacing)))

        if not beam_width:
            if vals:
                beam_width = vals.get("beam_width", None)
            if not beam_width:
                self.AddRuntimeMessage(Warning, "beam_width failed to collect data")
        if not isinstance(beam_width, float):
            raise TypeError("beam_width expected a float, got: {}".format(type(beam_width)))

        if not frame_depth:
            if vals:
                frame_depth = vals.get("frame_depth", None)
            if not frame_depth:
                self.AddRuntimeMessage(Warning, "frame_depth failed to collect data")
        if not isinstance(frame_depth, float):
            raise TypeError("frame_depth expected a float, got: {}".format(type(frame_depth)))

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None

        category_options = vals.get("options", None) if vals else None

        if category_options:
            if not options:
                options = category_options
            else:
                for key, value in category_options.items():
                    if options.get(key, None) is None:          # if key from category_options not in options
                        options[key] = value
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            if options[key].get(k) is None:
                                options[key][k] = v
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, CategoryRule):
                                sets = [set([rule.category_a, rule.category_b]) for rule in options[key]]
                                if set([v.category_a, v.category_b]) not in sets:
                                    options[key].append(v)

        if not options:
            options = {}

        surface_model = SurfaceModel(
            Brep.from_native(surface), stud_spacing, beam_width, frame_depth, z_axis, **options
        )

        debug_info = DebugInfomation()
        scene = Scene()
        model = surface_model.create_model()
        if CreateGeometry:
            for element in model.beams:
                scene.add(element.geometry)
                if element.debug_info:
                    debug_info.add_feature_error(element.debug_info)
        else:
            for element in model.beams:
                scene.add(element.blank)

        if debug_info.has_errors:
            self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

        geometry = scene.draw()

        return model, geometry, debug_info
