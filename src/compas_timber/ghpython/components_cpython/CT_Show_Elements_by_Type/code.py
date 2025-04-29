# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper

from compas.scene import Scene

from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class ShowElementsByType(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, model):
        if not item_input_valid_cpython(ghenv, model, "Model"):
            return
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
