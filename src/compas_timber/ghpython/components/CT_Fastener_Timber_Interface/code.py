from compas.geometry import Brep
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.elements import FastenerTimberInterface


class FastenerTimberInterfaceComponent(component):
    def RunScript(self, outline, thickness, drill_points, drill_diameters, extra_shapes, features):
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
        feat_list = []
        for feature in features:
            if feature:
                if feature.elements:
                    self.AddRuntimeMessage(Warning, "Features in the Fastener Timber Interface are applied by joints. Elements in feature definitions will be ignored")
                feat_list.append(feature)
        outline_points = [pt for pt in outline] if outline else None
        interface = FastenerTimberInterface(
            outline_points,
            thickness,
            holes,
            shapes=[Brep.from_native(brep) for brep in extra_shapes],
            features=feat_list,
        )
        return interface
