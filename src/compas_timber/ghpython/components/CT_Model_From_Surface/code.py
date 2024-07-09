"""Creates a Beam from a LineCurve."""

from compas.geometry import Brep
from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.Geometry import Brep as RhinoBrep
from Rhino.Geometry import Vector3d as RhinoVector

from compas_timber.design import DebugInfomation
from compas_timber.design import SurfaceModel


class SurfaceModelComponent(component):
    def RunScript(self, surface, stud_spacing, beam_width, frame_depth, z_axis, options, CreateGeometry=False):
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
