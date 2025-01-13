"""Creates a Beam from a LineCurve."""

import Rhino
from compas.geometry import Brep
from compas.scene import Scene
from compas.tolerance import Tolerance
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

        units = Rhino.RhinoDoc.ActiveDoc.GetUnitSystemName(True, True, True, True)
        tol = None
        if units == "m":
            tol = Tolerance(unit="M", absolute=1e-6, relative=1e-6)
        elif units == "cm":
            tol = Tolerance(unit="CM", absolute=1e-4, relative=1e-4)
        elif units == "mm":
            tol = Tolerance(unit="MM", absolute=1e-3, relative=1e-3)

        if not stud_spacing:
            self.AddRuntimeMessage(Warning, "Input parameter 'stud_spacing' failed to collect data, using default value of 625mm")
            if tol.unit == "M":
                stud_spacing = 0.625
            elif tol.unit == "MM":
                stud_spacing = 625.0
            elif tol.unit == "CM":
                stud_spacing = 62.5
        elif not isinstance(stud_spacing, float):
            raise TypeError("stud_spacing expected a float, got: {}".format(type(stud_spacing)))

        if not beam_width:
            self.AddRuntimeMessage(Warning, "Input parameter 'beam_width' failed to collect data, using default value of 60mm")
            if tol.unit == "M":
                beam_width = 0.06
            elif tol.unit == "MM":
                beam_width = 60.0
            elif tol.unit == "CM":
                beam_width = 6.0
        elif not isinstance(beam_width, float):
            raise TypeError("beam_width expected a float, got: {}".format(type(beam_width)))

        if not frame_depth:
            self.AddRuntimeMessage(Warning, "Input parameter 'frame_depth' failed to collect data, using default value of 140mm")
            if tol.unit == "M":
                frame_depth = 0.14
            elif tol.unit == "MM":
                frame_depth = 140.0
            elif tol.unit == "CM":
                frame_depth = 14.0
        elif not isinstance(frame_depth, float):
            raise TypeError("frame_depth expected a float, got: {}".format(type(frame_depth)))

        if z_axis is not None and not isinstance(z_axis, RhinoVector):
            raise TypeError("Expected a compas.geometry.Vector, got: {}".format(type(z_axis)))

        # reformat unset parameters for consistency
        if not z_axis:
            z_axis = None
        if not options:
            options = {}

        surface_model = SurfaceModel(Brep.from_native(surface), stud_spacing, beam_width, frame_depth, z_axis, tol, **options)

        debug_info = DebugInfomation()
        scene = Scene()
        model = surface_model.create_model()
        model.process_joinery()
        for f_def in surface_model.features:
            for element in f_def.elements:
                element.add_features(f_def.feature)
        if CreateGeometry:
            for element in model.elements():
                scene.add(element.geometry)
                if element.debug_info:
                    debug_info.add_feature_error(element.debug_info)
        else:
            for element in model.elements():
                scene.add(element.blank)

        if debug_info.has_errors:
            self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

        geometry = scene.draw()

        return model, geometry, debug_info
