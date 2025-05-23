# r: compas_timber>=0.15.3
"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import rhinoscriptsyntax as rs
import System
from compas.scene import Scene
from compas_rhino.conversions import line_to_compas
from compas_rhino.conversions import vector_to_compas

from compas_timber.elements import Beam as CTBeam
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython


class Beam_fromCurve(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self,
        centerline: System.Collections.Generic.List[object],
        z_vector: System.Collections.Generic.List[Rhino.Geometry.Vector3d],
        width: System.Collections.Generic.List[float],
        height: System.Collections.Generic.List[float],
        category: System.Collections.Generic.List[str],
        updateRefObj: bool,
    ):
        # minimum inputs required
        if not list_input_valid_cpython(ghenv, centerline, "Centerline"):
            return
        if not width:
            length = self._get_centerline_length(centerline)
            width = [length / 20]
        if not height:
            length = self._get_centerline_length(centerline)
            height = [length / 10]

        # reformat unset parameters for consistency
        if not z_vector:
            z_vector = [None]
        if not category:
            category = [None]

        beams = []
        blanks = []
        scene = Scene()

        if centerline and height and width:
            # check list lengths for consistency
            N = len(centerline)
            if len(z_vector) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'ZVector' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(width) not in (1, N):
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'W' I need either one or the same number of inputs as the Crv parameter.")
            if len(height) not in (1, N):
                ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'H' I need either one or the same number of inputs as the Crv parameter.")
            if len(category) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter."
                )

            # duplicate data if None or single value
            if len(z_vector) != N:
                z_vector = [z_vector[0] for _ in range(N)]
            if len(width) != N:
                width = [width[0] for _ in range(N)]
            if len(height) != N:
                height = [height[0] for _ in range(N)]
            if len(category) != N:
                category = [category[0] for _ in range(N)]

            for line, z, w, h, c in zip(centerline, z_vector, width, height, category):
                guid, geometry = self._get_guid_and_geometry(line)
                rhino_line = rs.coerceline(geometry)
                line = line_to_compas(rhino_line)

                z = vector_to_compas(z) if z else None
                beam = CTBeam.from_centerline(centerline=line, width=w, height=h, z_vector=z)
                beam.attributes["rhino_guid"] = str(guid) if guid else None
                beam.attributes["category"] = c
                if updateRefObj and guid:
                    update_rhobj_attributes_name(guid, "width", str(w))
                    update_rhobj_attributes_name(guid, "height", str(h))
                    update_rhobj_attributes_name(guid, "zvector", str(list(beam.frame.zaxis)))
                    update_rhobj_attributes_name(guid, "category", c)

                beams.append(beam)
                scene.add(beam.blank)

        blanks = scene.draw()

        return beams, blanks

    def _get_guid_and_geometry(self, line):
        # internalized curves and GH geometry will not have persistent GUIDs, referenced Rhino objects will
        # type hint on the input has to be 'ghdoc' for this to work
        guid = None
        geometry = line
        rhino_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(line)
        if rhino_obj:
            guid = line
            geometry = rhino_obj.Geometry
        return guid, geometry

    def _get_centerline_length(self, centerline):
        centerline_length = []
        for i in centerline:
            centerline_length.append(rs.CurveLength(i))
        if centerline_length:
            length_average = sum(centerline_length) / len(centerline_length)
        else:
            length_average = 1
        return length_average
