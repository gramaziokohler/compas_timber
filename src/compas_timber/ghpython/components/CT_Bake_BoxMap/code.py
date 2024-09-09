# flake8: noqa
import math
import random

import rhinoscriptsyntax as rs
from compas_rhino.conversions import frame_to_rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino import Render
from Rhino.Geometry import Interval
from Rhino.Geometry import Plane
from Rhino.RhinoDoc import ActiveDoc


class BakeBoxMap(component):
    def RunScript(self, Model, MapSize, bake):
        if MapSize and len(MapSize) != 3:
            self.AddRuntimeMessage(
                Error, "Input parameter MapSize requires exactly three float values (scale factors in x,y,z directions)"
            )
            return

        if MapSize:
            dimx, dimy, dimz = MapSize
        else:
            # for the pine 251 material bitmap, rotated
            dimx = 0.2
            dimy = 0.2
            dimz = 1.0

        if not Model:
            self.AddRuntimeMessage(Warning, "Input parameters Model failed to collect any Beam objects.")
            return

        if not bake:
            return

        try:
            frames = [frame_to_rhino(b.frame) for b in Model.beams]
            breps = [beam.geometry.native_brep for beam in Model.beams]

            if frames and breps:
                rs.EnableRedraw(False)

                for brep, frame in zip(breps, frames):
                    guid = ActiveDoc.Objects.Add(brep)
                    boxmap = self.create_box_map(frame, dimx, dimy, dimz)
                    ActiveDoc.Objects.ModifyTextureMapping(guid, 1, boxmap)
        finally:
            rs.EnableRedraw(True)

    @staticmethod
    def create_box_map(pln, sx, sy, sz):
        """
        pln: frame of beam box, where x=main axis, y=width, z=height
        sx,sy,sz: box map size in x,y,z direction
        """

        v = pln.YAxis
        w = pln.ZAxis
        pt = pln.Origin

        # random deviation
        a = math.pi * 0.5
        randangle = (random.random() - 0.5) * a
        v.Rotate(randangle, pln.XAxis)

        b = math.pi * 0.01
        randangle = (random.random() - 0.5) * b
        w.Rotate(randangle, pln.XAxis)

        randpos = sx * random.random()
        pt += pln.XAxis * randpos

        # create box mapping
        mappingPln = Plane(pt, w, v)
        dx = Interval(-sx * 0.5, sx * 0.5)
        dy = Interval(-sy * 0.5, sy * 0.5)
        dz = Interval(-sz * 0.5, sz * 0.5)

        BoxMap = Render.TextureMapping.CreateBoxMapping(mappingPln, dx, dy, dz, False)

        return BoxMap
