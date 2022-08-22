#from compas_timber.ghpython.components.version import VERSION_DATE, AUTHOR
#__author__ = AUTHOR
#__version__ = VERSION_DATE


__author__ = "aapolina"
__version__ = "2021.12.10"
                
import Rhino
import Rhino.Geometry as rg
from compas_timber.ghpython.components.CT_Get_Attributes.code import H, W, ZV, Cat, Gr
import rhinoscriptsyntax as rs

from compas_rhino.geometry import RhinoCurve
from compas_ghpython.utilities import unload_modules
from compas_timber.parts.beam import Beam as ctBeam
from compas_timber.utils.rhino_compas import rVec2cVec, cBox2rBox, rLine2cLine
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name


z_vector = ZV
width = W
height =  H
category = Cat
group =  Gr



if not refCrv:
    pass
else:
    n = len(refCrv)
    if not z_vector: z_vector=[None]
    if not category: category=[None]
    if not group: group=[None]
    if len(z_vector) not in (0,1,n): 
        raise UserWarning(" In 'z_vector' I need either none, one or the same number of inputs as the refCrv parameter.")
    if len(width) not in (1,n): 
        raise UserWarning(" In 'width' I need either one or the same number of inputs as the refCrv parameter.")
    if len(height) not in (1,n): 
        raise UserWarning(" In 'height' I need either one or the same number of inputs as the refCrv parameter.")
    if len(category) not in (0,1,n): 
        raise UserWarning(" In 'category' I need either none, one or the same number of inputs as the refCrv parameter.")
    if len(group) not in (0,1,n): 
        raise UserWarning(" In 'group' I need either none, one or the same number of inputs as the refCrv parameter.")

    if len(z_vector)!=n: z_vector = [z_vector[0] for _ in range(n)]
    if len(width)!=n: width = [width[0] for _ in range(n)]
    if len(height)!=n: height = [height[0] for _ in range(n)]
    if len(category)!=n: category = [category[0] for _ in range(n)]
    if len(group)!=n: group = [group[0] for _ in range(n)]


    Beam = []
    for guid,z,w,h,c,g  in zip(refCrv, z_vector,width, height, category, group):

        crv = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid).Geometry
        line = rg.Line(crv.PointAtStart,crv.PointAtEnd)
        
        line = rLine2cLine(line)
        if z: z = rVec2cVec(z) 
        else: None
        
        beam = ctBeam.from_centreline(line,z,w,h)
        shape = cBox2rBox(beam.shape)
        
        beam.attributes['rhino_guid']= guid
        beam.attributes['category']= c
        beam.attributes['group'] = g
        
        
        
        if update_attrs:
            update_rhobj_attributes_name(guid,"width", str(w))
            update_rhobj_attributes_name(guid,"height", str(h))
            update_rhobj_attributes_name(guid,"zaxis", str(list(beam.frame.zaxis)))
            update_rhobj_attributes_name(guid,"category", c)
        
        Beam.append(beam)
