# r: compas_timber>=0.15.3
import Grasshopper
import Rhino
import System
from compas.scene import SceneObject

from compas_timber.elements import PlateFastener


class PlateFastenerComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self, outline: Rhino.Geometry.Polyline, thickness: float, cutouts: System.Collections.Generic.List[Rhino.Geometry.Polyline], main_beam_interface, cross_beam_interface
    ):
        outline_points = [point for point in outline] if outline else None
        cutout_points = []
        if cutouts:
            for cutout in cutouts:
                cutout_points.append([pt for pt in cutout])
        if main_beam_interface and cross_beam_interface:
            interfaces = [main_beam_interface, cross_beam_interface]
        else:
            interfaces = []
        fastener = PlateFastener(
            outline=outline_points,
            thickness=thickness,
            interfaces=interfaces,
            cutouts=cutout_points,
        )
        shape = None
        if outline and thickness:
            shape = SceneObject(item=fastener.shape).draw()

        return fastener, shape
