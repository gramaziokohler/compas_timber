from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
import Rhino
from compas_timber.elements import FastenerTimberInterface
from compas.geometry import Brep
from compas.scene import Scene


class FastenerInterfaceComponent(component):
    def RunScript(self, outline_points, thickness, drill_points, drill_diameters, extra_shapes, features):
        holes = []
        if drill_points and drill_diameters:
            if len(drill_points) == len(drill_diameters):
                for pt, dia in zip(drill_points, drill_diameters):
                    holes.append({"point": pt, "diameter": dia, "vector": None, "through": True})
            elif len(drill_diameters) == 1:
                for pt in drill_points:
                    holes.append({"point": pt, "diameter": drill_diameters[0], "vector": None, "through": True})
            else:
                self.AddRuntimeMessage(
                    Error, " In 'drill_diameters' I need either one or the same number of inputs as the drill_points parameter."
                )
        fast_int = FastenerTimberInterface(outline_points, thickness, holes, shapes = [Brep.from_native(brep) for brep in extra_shapes], feature_defs = features)

        scene = Scene()
        scene.add(fast_int.shape)
        shape = scene.draw()

        return fast_int, shape
