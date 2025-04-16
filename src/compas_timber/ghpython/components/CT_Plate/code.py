"""Creates a Beam from a LineCurve."""

import rhinoscriptsyntax as rs
from compas.scene import Scene
from compas_rhino.conversions import curve_to_compas
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.elements import Plate as CTPlate
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid


class Plate(component):
    def RunScript(self, outline, outline_b, thickness, vector, category, updateRefObj):
        if not list_input_valid(self, outline, outline):
            return
        if not thickness and not outline_b:
            self.AddRuntimeMessage(Warning, "Input required on either 'Thickness' or 'outline_b")
            return
        if not outline_b:
            outline_b = [None]
        if not vector:
            vector = [None]
        if not category:
            category = [None]

        plates = []
        scene = Scene()

        # check list lengths for consistency
        N = len(outline)
        if len(thickness) not in (0, 1, N):
            print(" In 'T' I need either one or the same number of inputs as the Crv parameter.")
        if len(outline_b) not in (0, N):
            print(" In 'outline_b' I need either one or the same number of inputs as the Crv parameter.")
        if len(category) not in (0, 1, N):
            print(" In 'Category' I need either none, one or the same number of inputs as the Crv parameter.")
        if len(vector) not in (0, 1, N):
            print(" In 'Vector' I need either none, one or the same number of inputs as the Crv parameter.")

        # duplicate data if None or single value
        if len(outline_b) != N:
            outline_b = [outline_b[0] for _ in range(N)]
        if len(thickness) != N:
            thickness = [thickness[0] for _ in range(N)]
        if len(vector) != N:
            vector = [vector[0] for _ in range(N)]
        if len(category) != N:
            category = [category[0] for _ in range(N)]

        for line_a, line_b, t, v, c in zip(outline, outline_b, thickness, vector, category):
            guid_a, geometry_a = self._get_guid_and_geometry(line_a)
            rhino_polyline_a = rs.coercecurve(geometry_a)
            line_a = curve_to_compas(rhino_polyline_a)

            if line_b:
                guid_b, geometry_b = self._get_guid_and_geometry(line_b)
                rhino_polyline_b = rs.coercecurve(geometry_b)
                line_b = curve_to_compas(rhino_polyline_b)
                plate = CTPlate(line_a.points, line_b.points)
                plate.attributes["rhino_guid_a"] = str(guid_a) if guid_a else None
                if updateRefObj and guid_b:
                    update_rhobj_attributes_name(guid_b, "outline", str(line_b))

            else:
                print(v)
                plate = CTPlate.from_outline_thickness(line_a.points, t, vector_to_compas(v) if v else None)

            plate.attributes["rhino_guid_a"] = str(guid_a) if guid_a else None
            plate.attributes["category"] = c

            if updateRefObj and guid_a:
                update_rhobj_attributes_name(guid_a, "outline", str(line_a))
                update_rhobj_attributes_name(guid_a, "thickness", str(t))
                update_rhobj_attributes_name(guid_a, "category", c)

            plates.append(plate)
            scene.add(plate.shape())

        return plates, scene.draw()

    def _get_guid_and_geometry(self, line):  # TODO: move to ghpython_helpers
        # internalized curves and GH geometry will not have persistent GUIDs, referenced Rhino objects will
        # type hint on the input has to be 'ghdoc' for this to work
        guid = None
        geometry = line
        rhino_obj = ActiveDoc.Objects.FindId(line)

        if rhino_obj:
            guid = line
            geometry = rhino_obj.Geometry
        return guid, geometry
