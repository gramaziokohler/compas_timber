# flake8: noqa
from ghpythonlib.componentbase import executingcomponent as component
from compas.scene import Scene


class ShowElementsByType(component):
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
