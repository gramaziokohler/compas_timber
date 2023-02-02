"""Extracts main geometric characteristics of a beam."""
from compas.artists import Artist
from compas_rhino.conversions import box_to_rhino
from compas_rhino.conversions import frame_to_rhino
from compas_rhino.conversions import line_to_rhino_curve
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.utils.ghpython import list_input_valid


class MyComponent(component):
    def RunScript(self, Beam):
        if not Beam:
            self.AddRuntimeMessage(Warning, "Input parameter Beam failed to collect data")

        Frame = []
        Centerline = []
        Box = []
        Brep = []
        Width = []
        Height = []
        if list_input_valid(ghenv, Beam, "Beam"):
            Frame = [frame_to_rhino(b.frame) for b in Beam]
            Centerline = [line_to_rhino_curve(b.centerline) for b in Beam]
            Box = [box_to_rhino(b.shape) for b in Beam]
            # Brep = [Artist(b.get_geometry(True)).draw() for b in Beam]
            Brep = [b.get_geometry().native_brep for b in Beam]
            Width = [b.width for b in Beam]
            Height = [b.height for b in Beam]

        return (Frame, Centerline, Box, Brep, Width, Height)
