# r: compas_timber>=0.15.3
# flake8: noqa
import math
import random

import Grasshopper
import System
import Rhino
import rhinoscriptsyntax as rs
from compas_rhino.conversions import frame_to_rhino
from compas_timber.ghpython import item_input_valid_cpython

from Rhino import Render
from Rhino.Geometry import Interval
from Rhino.Geometry import Plane


class BakeBoxMap(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model, map_size: System.Collections.Generic.List[float], bake: bool):
        if map_size and len(map_size) != 3:
            ghenv.Component.AddRuntimeMessage(
                Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, "Input parameter MapSize requires exactly three float values (scale factors in x,y,z directions)"
            )
            return

        unit_system = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

        if map_size:
            dimx, dimy, dimz = map_size
        else:
            # for the pine 251 material bitmap, rotated
            if unit_system == Rhino.UnitSystem.Meters:
                dimx = 0.2
                dimy = 0.2
                dimz = 1.0
            if unit_system == Rhino.UnitSystem.Centimeters:
                dimx = 20
                dimy = 20
                dimz = 100
            if unit_system == Rhino.UnitSystem.Millimeters:
                dimx = 200
                dimy = 200
                dimz = 1000

        if not item_input_valid_cpython(ghenv, model, "Model"):
            return

        if not bake:
            return

        try:
            frames = [frame_to_rhino(b.frame) for b in model.beams]
            breps = [beam.geometry.native_brep for beam in model.beams]

            if frames and breps:
                rs.EnableRedraw(False)

                for brep, frame in zip(breps, frames):
                    guid = Rhino.RhinoDoc.ActiveDoc.Objects.Add(brep)
                    boxmap = self.create_box_map(frame, dimx, dimy, dimz)
                    Rhino.RhinoDoc.ActiveDoc.Objects.ModifyTextureMapping(guid, 1, boxmap)
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
