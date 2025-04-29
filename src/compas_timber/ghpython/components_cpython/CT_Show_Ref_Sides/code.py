# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System
import rhinoscriptsyntax as rs


from compas_rhino.conversions import frame_to_rhino
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython


class ShowElementFaces(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, element: System.Collections.Generic.List[object], ref_side_index: System.Collections.Generic.List[int]):
        if not list_input_valid_cpython(ghenv, element, "Element"):
            return
        self.pl = []
        self.txt = []
        self.ht = []
        srfs = []
        if not ref_side_index:
            ref_side_index = [0]
        if not len(ref_side_index) == len(element):
            ref_side_index = [ref_side_index[0] for _ in element]

        for b, i in zip(element, ref_side_index):
            srfs.append(self.get_srf(b, i))
            ht = 1000
            for side_index in range(len(b.ref_sides)):
                surface = b.side_as_surface(side_index)
                ht = min([self.ht, surface.xsize / 6.0, surface.ysize / 6.0])
            for side_index in range(len(b.ref_sides)):
                surface = b.side_as_surface(side_index)
                frame = b.ref_sides[side_index]
                frame.point = surface.point_at(0, ht / 4.0)

                self.pl.append(frame_to_rhino(frame))
                self.txt.append(surface.name)
                self.ht.append(ht)

        return srfs

    def get_srf(self, element, ref_side_index):
        face = element.side_as_surface(ref_side_index)
        rh_srf = rs.AddPlaneSurface(frame_to_rhino(face.frame), face.xsize, face.ysize)
        return rh_srf

    def DrawViewportWires(self, arg):
        if ghenv.Component.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw3dText_5.htm
        for p, t, h in zip(self.pl, self.txt, self.ht):
            arg.Display.Draw3dText(t, col, p, h, "Verdana", True, False)
