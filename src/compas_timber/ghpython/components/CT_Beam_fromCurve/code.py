"""Creates a Beam from a LineCurve."""

import rhinoscriptsyntax as rs
from compas.scene import Scene
from compas_rhino.conversions import line_to_compas
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.elements import Beam as CTBeam
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class Beam_fromCurve(component):
    def RunScript(self, centerline, z_vector, width, height, category, BTLx, updateRefObj):
        # minimum inputs required
        if not centerline:
            self.AddRuntimeMessage(Warning, "Input parameter 'Centerline' failed to collect data")
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
        if BTLx.BranchCount == 0:  # if no BTLx input, add an empty branch
            BTLx.Add(None, GH_Path(0))

        beams = []
        blanks = []
        scene = Scene()

        if centerline and height and width:
            # check list lengths for consistency
            N = len(centerline)
            if len(z_vector) not in (0, 1, N):
                self.AddRuntimeMessage(Error, " In 'ZVector' I need either none, one or the same number of inputs as the Crv parameter.")
            if len(width) not in (1, N):
                self.AddRuntimeMessage(Error, " In 'W' I need either one or the same number of inputs as the Crv parameter.")
            if len(height) not in (1, N):
                self.AddRuntimeMessage(Error, " In 'H' I need either one or the same number of inputs as the Crv parameter.")
            if len(category) not in (0, 1, N):
                self.AddRuntimeMessage(Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter.")
            if BTLx.BranchCount not in (0, 1, N):
                self.AddRuntimeMessage(Error, " In 'BTLx' I need either none, one or the same number of tree branches as the Crv parameter.")
            BTLx = [[b for b in BTLx.Branch(i)] for i in range(BTLx.BranchCount)]

            # duplicate data if None or single value
            if len(z_vector) != N:
                z_vector = [z_vector[0] for _ in range(N)]
            if len(width) != N:
                width = [width[0] for _ in range(N)]
            if len(height) != N:
                height = [height[0] for _ in range(N)]
            if len(category) != N:
                category = [category[0] for _ in range(N)]
            if len(BTLx) != N:
                BTLx = [BTLx[0] for _ in range(N)]

            for line, z, w, h, c, b in zip(centerline, z_vector, width, height, category, BTLx):
                guid, geometry = self._get_guid_and_geometry(line)
                rhino_line = rs.coerceline(geometry)
                line = line_to_compas(rhino_line)
                z = vector_to_compas(z) if z else None
                beam = CTBeam.from_centerline(centerline=line, width=w, height=h, z_vector=z)
                beam.attributes["rhino_guid"] = str(guid) if guid else None
                beam.attributes["category"] = c
                beam.add_features([feat for feat in b if feat])
                if updateRefObj and guid:
                    update_rhobj_attributes_name(guid, "width", str(w))
                    update_rhobj_attributes_name(guid, "height", str(h))
                    update_rhobj_attributes_name(guid, "zvector", str(list(beam.frame.zaxis)))
                    update_rhobj_attributes_name(guid, "category", c)

                beams.append(beam)
                scene.add(beam.geometry)  # visualize beams with features applied. returns beam.blank if no features.

        blanks = scene.draw()

        return beams, blanks

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

    def _get_centerline_length(self, centerline):
        centerline_length = []
        for i in centerline:
            centerline_length.append(rs.CurveLength(i))
        if centerline_length:
            length_average = sum(centerline_length) / len(centerline_length)
        else:
            length_average = 1
        return length_average
