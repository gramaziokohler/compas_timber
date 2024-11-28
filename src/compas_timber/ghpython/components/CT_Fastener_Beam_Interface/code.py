from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from compas_timber.design import FeatureDefinition
from compas_timber.elements import FastenerTimberInterface
from compas.geometry import Brep
from compas.scene import Scene

class MyComponent(component):

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
                raise Warning("Number of diameters must either match the number of points or be a single value")

        features = [feature.feature if isinstance(feature, FeatureDefinition) else feature for feature in features]

        fast_int = FastenerTimberInterface(outline_points, thickness, holes, shapes = [Brep.from_native(brep) for brep in extra_shapes], features = features)

        shape = None
        if outline_points:
            scene = Scene()
            scene.add(fast_int.shape)
            shape = scene.draw()

        return fast_int, shape
