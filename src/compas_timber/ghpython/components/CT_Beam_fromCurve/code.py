"""Creates a Beam from a LineCurve."""
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
from compas_rhino.conversions import line_to_compas
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.parts.beam import Beam as ctBeam


class MyComponent(component):
    
    def RunScript(self, Centerline, ZVector, Width, Height, Category, Group):

        #minimum inputs required
        if not Centerline:
            ghenv.Component.AddRuntimeMessage(Warning, "Input parameter 'Centerline' failed to collect data")
        if not Width:
            ghenv.Component.AddRuntimeMessage(Warning, "Input parameter 'Width' failed to collect data")
        if not Height:
            ghenv.Component.AddRuntimeMessage(Warning, "Input parameter 'Height' failed to collect data")
        
        #reformat unset parameters for consistency
        if not ZVector:
            ZVector = [None]
        if not Category:
            Category = [None]
        if not Group:
            Group = [None]
        
        
        if Centerline and Height and Width:
            # check list lengths for consistency
            N = len(Centerline)
            if len(ZVector) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Error, " In 'ZVector' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(Width) not in (1, N):
                ghenv.Component.AddRuntimeMessage(
                    Error, " In 'W' I need either one or the same number of inputs as the Crv parameter."
                )
            if len(Height) not in (1, N):
                ghenv.Component.AddRuntimeMessage(
                    Error, " In 'H' I need either one or the same number of inputs as the Crv parameter."
                )
            if len(Category) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(Group) not in (0, 1, N):
                ghenv.Component.AddRuntimeMessage(
                    Error, " In 'Group' I need either none, one or the same number of inputs as the Crv parameter."
                )
        
            # duplicate data if None or single value
            if len(ZVector) != N:
                ZVector = [ZVector[0] for _ in range(N)]
            if len(Width) != N:
                Width = [Width[0] for _ in range(N)]
            if len(Height) != N:
                Height = [Height[0] for _ in range(N)]
            if len(Category) != N:
                Category = [Category[0] for _ in range(N)]
            if len(Group) != N:
                Group = [Group[0] for _ in range(N)]
        
            Beam = []
            for crv, z, w, h, c, g in zip(Centerline, ZVector, Width, Height, Category, Group):
                if crv == None or w == None or h == None:
                    ghenv.Component.AddRuntimeMessage(Warning, "Some of the input values are Null")
                else:
                    line = rg.Line(crv.PointAtStart, crv.PointAtEnd)
        
                    line = line_to_compas(line)
                    if z:
                        z = vector_to_compas(z)
                    else:
                        None
        
                    beam = ctBeam.from_centerline(centerline=line, width=w, height=h,z_vector=z, geometry_type='brep')
        
                    beam.attributes["rhino_guid"] = None
                    beam.attributes["category"] = c
                    beam.attributes["group"] = g
        
                    Beam.append(beam)

        return Beam
