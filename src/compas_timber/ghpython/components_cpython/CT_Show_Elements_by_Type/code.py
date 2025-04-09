# flake8: noqa
import Grasshopper

from compas.scene import Scene


class ShowElementsByType(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        beam_scene = Scene()
        plate_scene = Scene()
        fastener_scene = Scene()

        for beam in model.beams:
            beam_scene.add(beam._geometry or beam.blank)
        for plate in model.plates:
            plate_scene.add(plate._geometry or plate.blank)
        for fastener in model.fasteners:
            fastener_scene.add(fastener.geometry)

        return beam_scene.draw(), plate_scene.draw(), fastener_scene.draw()
