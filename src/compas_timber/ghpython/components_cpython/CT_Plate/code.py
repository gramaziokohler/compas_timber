# r: compas_timber>=1.0.0
"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import rhinoscriptsyntax as rs
import System
from compas.scene import Scene
from compas_rhino.conversions import polyline_to_compas
from compas_rhino.conversions import vector_to_compas

from compas_timber.elements import Plate as CTPlate
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class Plate(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, outline, thickness: float, vector: Rhino.Geometry.Vector3d, openings: System.Collections.Generic.List[object], category: str, updateRefObj: bool):
        # minimum inputs required

        if not item_input_valid_cpython(ghenv, outline, "Outline") or not item_input_valid_cpython(ghenv, thickness, "Thickness"):
            return
        scene = Scene()
        guid, geometry = self._get_guid_and_geometry(outline)
        rhino_polyline = rs.coercecurve(geometry)
        line = polyline_to_compas(rhino_polyline.ToPolyline())
        v = vector_to_compas(vector)
        o = []
        if openings:
            for o_outline in openings:
                o_guid, o_geometry = self._get_guid_and_geometry(o_outline)
                o_rhino_polyline = rs.coercecurve(o_geometry)
                o.append(polyline_to_compas(o_rhino_polyline.ToPolyline()))
        v = vector_to_compas(vector)
        plate = CTPlate.from_outline_thickness(line, thickness, vector=v, openings=o)
        print(plate.geometry)
        plate.attributes["rhino_guid"] = str(guid) if guid else None
        plate.attributes["category"] = category

        if updateRefObj and guid:
            update_rhobj_attributes_name(guid, "outline", str(outline))
            update_rhobj_attributes_name(guid, "thickness", str(thickness))
            update_rhobj_attributes_name(guid, "category", category)

        scene.add(plate.shape)
        geo = scene.draw()
        return plate, geo

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
