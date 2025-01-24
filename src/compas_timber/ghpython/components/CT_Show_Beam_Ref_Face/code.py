import rhinoscriptsyntax as rs
from compas.geometry import Line
from compas.scene import Scene
from compas_rhino.conversions import frame_to_rhino
from ghpythonlib.componentbase import executingcomponent as component


class BTLxRefFace(component):
    def RunScript(self, element, ref_side_index):
        if not element:
            return
        if not ref_side_index:
            ref_side_index = 0
        return self.get_srf(element, ref_side_index)

    def get_srf(self, element, ref_side_index):
        face = element.side_as_surface(ref_side_index)
        rh_srf = rs.AddPlaneSurface(frame_to_rhino(face.frame), face.xsize, face.ysize)
        ln = Line(face.point_at(0, face.ysize / 3.0), face.point_at(face.ysize * 3 / 4, 0))
        scene = Scene()
        scene.add(ln)
        ln = scene.draw()
        return rh_srf, ln[0]
