# flake8: noqa
import math
import random

import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import scriptcontext as sc
from compas.artists import Artist
from compas_rhino.conversions import frame_to_rhino
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid


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
    mappingPln = rg.Plane(pt, w, v)
    dx = rg.Interval(-sx * 0.5, sx * 0.5)
    dy = rg.Interval(-sy * 0.5, sy * 0.5)
    dz = rg.Interval(-sz * 0.5, sz * 0.5)

    BoxMap = Rhino.Render.TextureMapping.CreateBoxMapping(mappingPln, dx, dy, dz, False)

    return BoxMap, mappingPln


if not MapSize:
    # for the pine 251 material bitmap, rotated
    dimx = 0.2
    dimy = 0.2
    dimz = 1.0

elif len(MapSize) != 3:
    ghenv.Component.AddRuntimeMessage(
        Error, "Input parameter MapSize requires exactly three float values (scale factors in x,y,z directions)"
    )
else:
    dimx, dimy, dimz = MapSize

_inputok = list_input_valid(ghenv, Beam, "Beam")

if _inputok and Bake:
    frames = [frame_to_rhino(b.frame) for b in Beam]
    breps = [Artist(b.get_geometry(True)).draw() for b in Beam]

    if frames and breps:
        rs.EnableRedraw(False)
        sc.doc = Rhino.RhinoDoc.ActiveDoc

        for brep, frame in zip(breps, frames):
            attributes = None
            guid = sc.doc.Objects.Add(brep, attributes)
            boxmap, map_pln = create_box_map(frame, dimx, dimy, dimz)
            sc.doc.Objects.ModifyTextureMapping(guid, 1, boxmap)

        sc.doc = ghdoc
        rs.EnableRedraw(True)
        rs.Redraw()

else:
    sc.doc = ghdoc
    rs.EnableRedraw(True)
    rs.Redraw()
