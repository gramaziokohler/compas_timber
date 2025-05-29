# flake8: noqa
import System
import rhinoscriptsyntax as rs
from ghpythonlib.componentbase import executingcomponent as component

from compas_rhino.conversions import frame_to_rhino


class ShowBeamFaces(component):
    def RunScript(self, Beam, RefSideIndex):
        if not Beam:
            return None
        self.pl = []
        self.txt = []
        self.ht = []
        srfs = []
        if not RefSideIndex:
            RefSideIndex = [0]
        if not len(RefSideIndex) == len(Beam):
            RefSideIndex = [RefSideIndex[0] for _ in Beam]

        for b, i in zip(Beam, RefSideIndex):
            srfs.append(self.get_srf(b, i))
            ht = 1000
            for side_index in range(len(b.ref_sides)):
                surface = b.side_as_surface(side_index)
                ht = min([ht, surface.xsize / 6.0, surface.ysize / 6.0])
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
        if self.Locked:
            return
        col = System.Drawing.Color.FromArgb(255, 255, 255, 255)
        # https://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Display_DisplayPipeline_Draw3dText_5.htm
        for p, t, h in zip(self.pl, self.txt, self.ht):
            arg.Display.Draw3dText(t, col, p, h, "Verdana", True, False)
