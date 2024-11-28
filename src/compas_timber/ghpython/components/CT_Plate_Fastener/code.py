from ast import main
from ghpythonlib.componentbase import executingcomponent as component
from compas_timber.elements import PlateFastener
from compas.scene import SceneObject
from compas_rhino.conversions import curve_to_compas


class MyComponent(component):

    def RunScript(self, outline, cutouts, main_beam_interface, cross_beam_interface):
        if not outline and main_beam_interface and cross_beam_interface:
            return
        outline_curve = curve_to_compas(outline)
        cutout_curves = [curve_to_compas(cutout) for cutout in cutouts]
        fastener = PlateFastener.from_outline_thickness_interfaces_cutouts(outline_curve, thickness = 4, interfaces = [main_beam_interface, cross_beam_interface], cutouts=cutout_curves)
        return fastener,  SceneObject(item=fastener.shape).draw()
