"""Creates a Beam from a LineCurve."""

import rhinoscriptsyntax as rs
from compas.scene import Scene
from compas_rhino.conversions import curve_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.elements import Plate as CTPlate
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Plate(component):
    def RunScript(self, outline, thickness, vector, category, updateRefObj):
        # minimum inputs required
        if not outline:
            self.AddRuntimeMessage(Warning, "Input parameter 'Outline' failed to collect data")
        if not thickness:
            self.AddRuntimeMessage(Warning, "Input parameter 'Thickness' failed to collect data")
        if not vector:
            vector = [None]
        # reformat unset parameters for consistency

        if not category:
            category = [None]

        plates = []
        scene = Scene()

        if outline and thickness:
            # check list lengths for consistency
            N = len(outline)
            if len(thickness) not in (1, N):
                self.AddRuntimeMessage(
                    Error, " In 'T' I need either one or the same number of inputs as the Crv parameter."
                )
            if len(category) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(vector) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error, " In 'Vector' I need either none, one or the same number of inputs as the Crv parameter."
                )

            # duplicate data if None or single value
            if len(thickness) != N:
                thickness = [thickness[0] for _ in range(N)]
            if len(vector) != N:
                vector = [vector[0] for _ in range(N)]
            if len(category) != N:
                category = [category[0] for _ in range(N)]

            for line, t, v, c in zip(outline, thickness, vector, category):
                guid, geometry = self._get_guid_and_geometry(line)
                rhino_polyline = rs.coercecurve(geometry)
                line = curve_to_compas(rhino_polyline)

                plate = CTPlate.from_outline_and_thickness(line, t, v)
                plate.attributes["rhino_guid"] = str(guid) if guid else None
                plate.attributes["category"] = c

                if updateRefObj and guid:
                    update_rhobj_attributes_name(guid, "outline", str(line))
                    update_rhobj_attributes_name(guid, "thickness", str(t))
                    update_rhobj_attributes_name(guid, "category", c)

                plates.append(plate)
                scene.add(plate.shape)

        geo = scene.draw()

        return plates, geo

    def _get_guid_and_geometry(self, line):
        # internalized curves and GH geometry will not have persistent GUIDs, referenced Rhino objects will
        # type hint on the input has to be 'ghdoc' for this to work
        guid = None
        geometry = line
        rhino_obj = ActiveDoc.Objects.FindId(line)

        if rhino_obj:
            guid = line
            geometry = rhino_obj.Geometry
        return guid, geometry
