"""
TODO: Add description

COMPAS Timber v0.1.0
"""
import System
import Grasshopper, GhPython
from ghpythonlib.componentbase import executingcomponent as component

import Rhino     
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs

class MyComponent(component):
    
    def RunScript(self, curve_guid, z_vector, width, height, attributes, reload):
        __author__ = "aapolina"
        __version__ = "2021.12.10"
                


        from compas_ghpython.utilities import unload_modules
        #from compas_rhino.conversions import vector_to_compas, box_to_rhino, line_to_compas
        from compas_timber.parts.beam import Beam
        from compas_timber.utils.rhino_compas import rVec2cVec, cBox2rBox, rLine2cLine
        from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name
                        
        if not (curve_guid and width and height): 
            return None
            
        crv = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(curve_guid).Geometry
        line = rg.Line(crv.PointAtStart,crv.PointAtEnd)
                
        line = rLine2cLine(line)
        if z_vector: z_vector = rVec2cVec(z_vector) 
        else: None
                
        beam = Beam.from_centreline(line,z_vector,width,height)
        shape = cBox2rBox(beam.shape)
                
        beam.attributes['rhino_guid']=curve_guid
        update_rhobj_attributes_name(curve_guid,"width", str(width))
        update_rhobj_attributes_name(curve_guid,"height", str(height))
        update_rhobj_attributes_name(curve_guid,"zaxis", str(list(beam.frame.zaxis)))
        
        for attr in attributes:
            for k in attr:
                beam.attributes[k]=attr[k]
                update_rhobj_attributes_name(curve_guid,str(k), str(attr[k]))

        return beam
