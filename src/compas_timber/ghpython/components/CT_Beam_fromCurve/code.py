__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

import Rhino.Geometry as rg
import rhinoscriptsyntax as rs

from compas_rhino.geometry import RhinoCurve
from compas_rhino.conversions import vector_to_compas, line_to_compas
from compas_ghpython.utilities import unload_modules
from compas_timber.parts.beam import Beam as ctBeam
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name

import Grasshopper.Kernel as ghk
warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

if not LineCrv:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter LineCrv failed to collect data")
if not Width: 
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Width failed to collect data")
if not Height: 
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter Height failed to collect data")

#=============================

if not ZVector: ZVector=[None]
if not Category: Category=[None]
if not Group: Group=[None]


if LineCrv and Height and Width:
    #check list lengths for consistency
    n = len(LineCrv)
    if len(ZVector) not in (0,1,n): 
        ghenv.Component.AddRuntimeMessage(error, " In 'ZVector' I need either none, one or the same number of inputs as the Crv parameter.")
    if len(Width) not in (1,n): 
        ghenv.Component.AddRuntimeMessage(error, " In 'W' I need either one or the same number of inputs as the Crv parameter.")
    if len(Height) not in (1,n): 
        ghenv.Component.AddRuntimeMessage(error, " In 'H' I need either one or the same number of inputs as the Crv parameter.")
    if len(Category) not in (0,1,n): 
        ghenv.Component.AddRuntimeMessage(error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter.")
    if len(Group) not in (0,1,n): 
        ghenv.Component.AddRuntimeMessage(error, " In 'Group' I need either none, one or the same number of inputs as the Crv parameter.")

    #duplicate data
    if len(ZVector)!=n: ZVector = [ZVector[0] for _ in range(n)]
    if len(Width)!=n: Width = [Width[0] for _ in range(n)]
    if len(Height)!=n: Height = [Height[0] for _ in range(n)]
    if len(Category)!=n: Category = [Category[0] for _ in range(n)]
    if len(Group)!=n: Group = [Group[0] for _ in range(n)]


    Beam = []
    for crv,z,w,h,c,g  in zip(LineCrv, ZVector,Width, Height, Category, Group):
        if crv==None or w==None or h==None:
            ghenv.Component.AddRuntimeMessage(warning, "Some of the input values are Null")
        else:
            line = rg.Line(crv.PointAtStart,crv.PointAtEnd)
            
            line = line_to_compas(line)
            if z: z = vector_to_compas(z) 
            else: None
            
            beam = ctBeam.from_centreline(line,z,w,h)

            beam.attributes['rhino_guid']= None
            beam.attributes['category']= c
            beam.attributes['group'] = g

            Beam.append(beam)
