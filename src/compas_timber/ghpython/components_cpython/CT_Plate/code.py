"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import rhinoscriptsyntax as rs
import System
from compas.scene import Scene
from compas_rhino.conversions import curve_to_compas
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.elements import Plate as CTPlate
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Plate(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self,
        outline: System.Collections.Generic.List[Rhino.Geometry.Polyline],
        thickness: System.Collections.Generic.List[float],
        vector: System.Collections.Generic.List[Rhino.Geometry.Vector3d],
        category: System.Collections.Generic.List[str],
        updateRefObj: bool,
    ):
        # minimum inputs required
        if not outline:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'Outline' failed to collect data")
        if not thickness:
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Input parameter 'Thickness' failed to collect data")
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
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'T' I need either one or the same number of inputs as the Crv parameter.")
            if len(category) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(vector) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'Vector' I need either none, one or the same number of inputs as the Crv parameter."
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

                plate = CTPlate(line, t, v)
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
