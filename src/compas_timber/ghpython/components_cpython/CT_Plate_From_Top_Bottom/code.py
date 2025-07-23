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
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class PlateFromTopBottom(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self,
            top,
            bottom,
            openings: System.Collections.Generic.List[object],
            category: str,
            updateRefObj: bool):
        # minimum inputs required

        if not item_input_valid_cpython(ghenv, top, "top") or not item_input_valid_cpython(ghenv, bottom, "bottom"):
            return
        else:
            if not category:
                category = None
            plates = []
            scene = Scene()
            # check list lengths for consistency

        t_guid, t_geometry = self._get_guid_and_geometry(top)
        b_guid, b_geometry = self._get_guid_and_geometry(bottom)
        t_rhino_polyline = rs.coercecurve(t_geometry)
        b_rhino_polyline = rs.coercecurve(b_geometry)
        top = polyline_to_compas(t_rhino_polyline.ToPolyline())
        bottom = polyline_to_compas(b_rhino_polyline.ToPolyline())

        o = []
        if openings:
            for o_outline in openings:
                _, o_geometry = self._get_guid_and_geometry(o_outline)
                o_rhino_polyline = rs.coercecurve(o_geometry)
                o.append(polyline_to_compas(o_rhino_polyline.ToPolyline()))

        plate = CTPlate(top, bottom, openings=o)
        plate.attributes["rhino_guid_a"] = str(t_guid) if t_guid else None
        plate.attributes["rhino_guid_b"] = str(b_guid) if b_guid else None
        plate.attributes["category"] = category

        if updateRefObj and t_guid:
            update_rhobj_attributes_name(t_guid, "outline_a", str(top))
            update_rhobj_attributes_name(b_guid, "outline_b", str(bottom))
            update_rhobj_attributes_name(t_guid, "category", category)

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
