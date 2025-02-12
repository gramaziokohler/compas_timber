"""Creates a Beam from a LineCurve."""

import rhinoscriptsyntax as rs
from compas.geometry import Brep
from compas.scene import Scene
from compas_rhino.conversions import curve_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.design import ContainerDefinition
from compas_timber.elements import Wall
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class WallComponent(component):
    def RunScript(self, surface, thickness, config_set):
        # minimum inputs required
        if not surface:
            self.AddRuntimeMessage(Warning, "Input parameter 'Surface' failed to collect data")
        if not thickness:
            self.AddRuntimeMessage(Warning, "Input parameter 'Thickness' failed to collect data")

        if not surface or not thickness:
            return

        if not config_set:
            config_set = [None]

        scene = Scene()
        containers = []
        # check list lengths for consistency
        N = len(surface)
        if len(thickness) not in (1, N):
            self.AddRuntimeMessage(Error, " In 'T' I need either one or the same number of inputs as the Crv parameter.")

        # duplicate data if None or single value
        if len(thickness) != N:
            thickness = [thickness[0] for _ in range(N)]

        if len(config_set) != N:
            config_set = [config_set[0] for _ in range(N)]

        for srf, t, c_s in zip(surface, thickness, config_set):
            wall = Wall.from_brep(Brep.from_native(srf), t)

            containers.append(ContainerDefinition(wall, c_s))
            scene.add(wall.geometry)

        geo = scene.draw()

        return containers, geo
