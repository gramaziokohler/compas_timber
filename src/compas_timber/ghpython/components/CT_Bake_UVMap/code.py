import Rhino.Geometry as rg
import scriptcontext as sc
import math
import copy
import Rhino.Render as rr
import rhinoscriptsyntax as rs
import Rhino
import random

from compas_rhino.conversions import frame_to_rhino

import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

if not Assembly:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Assembly faild to collect data")
elif not Assembly.beams:
    ghenv.Component.AddRuntimeMessage(warning, "No Beams in the Assembly")

def create_box_map(pln,sx,sy,sz):
    """
    pln: frame of beam box, where x=main axis, y=width, z=height
    sx,sy,sz: box map size in x,y,z direction
    """

    v = pln.YAxis
    w = pln.ZAxis
    pt = pln.Origin

    #random deviation 
    a = math.pi*0.5
    randangle = (random.random()-0.5)*a
    v.Rotate(randangle,pln.XAxis)
    
    b = math.pi*0.01
    randangle = (random.random()-0.5)*b
    w.Rotate(randangle,pln.XAxis)
    
    randpos = sx*random.random()
    pt += pln.XAxis*randpos
    
    #create box mapping
    mappingPln = rg.Plane(pt, w, v)
    dx = rg.Interval(-sx*0.5,sx*0.5)
    dy = rg.Interval(-sy*0.5,sy*0.5)
    dz = rg.Interval(-sz*0.5,sz*0.5)

    BoxMap = Rhino.Render.TextureMapping.CreateBoxMapping(mappingPln, dx, dy, dz, False)

    return BoxMap, mappingPln


if not MapSize:
    #for the pine 251 material bitmap, rotated
    dimx = 0.2
    dimy = 0.2
    dimz = 1.0
else:
    dimx,dimy,dimz = MapSize

if Bake:
    frames = [frame_to_rhino(beam.frame) for beam in Assembly.beams]
    breps = [beam.brep for beam in Assembly.beams]
    
    if frames and breps:
        rs.EnableRedraw(False)
        sc.doc = Rhino.RhinoDoc.ActiveDoc
    
        for brep, frame in zip(breps,frames):
            attributes = None
            guid = sc.doc.Objects.Add(brep, attributes)
            boxmap,map_pln = create_box_map(frame,dimx,dimy,dimz)
            sc.doc.Objects.ModifyTextureMapping(guid, 1, boxmap)

        sc.doc = ghdoc
        rs.EnableRedraw(True)
        rs.Redraw()

else:
    sc.doc = ghdoc
    rs.EnableRedraw(True)
    rs.Redraw()
