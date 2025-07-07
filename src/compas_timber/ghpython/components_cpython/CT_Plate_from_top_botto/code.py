# r: compas_timber>=0.15.3
"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import rhinoscriptsyntax as rs
import System
from compas.scene import Scene
from compas_rhino.conversions import polyline_to_compas

from compas_timber.elements import Plate as CTPlate
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython


class PlateFromTopBottom(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self,
            Top: System.Collections.Generic.List[object],
            Bottom: System.Collections.Generic.List[object],
            category: System.Collections.Generic.List[str],
            updateRefObj: bool):
        # minimum inputs required

        if not list_input_valid_cpython(ghenv, Top, "Outline") or not list_input_valid_cpython(ghenv, Bottom, "Thickness"):
            return
        else:
            if not category:
                category = [None]
            plates = []
            scene = Scene()
            # check list lengths for consistency
            if len(Top) != len(Bottom):
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " `Top` and `Bottom` must have the same number of elements.")
            if len(category) not in (0, 1, len(Top)):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'Category' I need either none, one or the same number of inputs as the `Top` parameter."
                )

            # duplicate data if None or single value
            if len(category) != len(Top):
                category = [category[0] for _ in range(len(Top))]

            for top_line, bottom_line, c in zip(Top, Bottom, category):
                t_guid, t_geometry = self._get_guid_and_geometry(top_line)
                b_guid, b_geometry = self._get_guid_and_geometry(bottom_line)
                t_rhino_polyline = rs.coercecurve(t_geometry)
                b_rhino_polyline = rs.coercecurve(b_geometry)
                top_line = polyline_to_compas(t_rhino_polyline.ToPolyline())
                bottom_line = polyline_to_compas(b_rhino_polyline.ToPolyline())

                plate = CTPlate(top_line, bottom_line)
                plate.attributes["rhino_guid_a"] = str(t_guid) if t_guid else None
                plate.attributes["rhino_guid_b"] = str(b_guid) if b_guid else None
                plate.attributes["category"] = c

                if updateRefObj and t_guid:
                    update_rhobj_attributes_name(t_guid, "outline_a", str(top_line))
                    update_rhobj_attributes_name(b_guid, "outline_b", str(bottom_line))
                    update_rhobj_attributes_name(t_guid, "category", c)

                plates.append(plate)
                scene.add(plate.shape)

        geo = scene.draw()

        return plates, geo

    def _get_guid_and_geometry(self, line):  # TODO: move to ghpython_helpers
        # internalized curves and GH geometry will not have persistent GUIDs, referenced Rhino objects will
        # type hint on the input has to be 'ghdoc' for this to work
        guid = None
        geometry = line
        rhino_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(line)

        if rhino_obj:
            guid = line
            geometry = rhino_obj.Geometry
        return guid, geometry
