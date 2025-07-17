# r: compas_timber>=0.15.3
"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import System
from compas.geometry import Brep
from compas.scene import Scene

from compas_timber.design import ContainerDefinition
from compas_timber.elements import Wall
from compas_timber.ghpython.ghcomponent_helpers import list_input_valid_cpython


class WallComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self, surface: System.Collections.Generic.List[Rhino.Geometry.Brep], thickness: System.Collections.Generic.List[float], config_set: System.Collections.Generic.List[object]
    ):
        # minimum inputs required
        if not list_input_valid_cpython(ghenv, surface, "Surface") or not list_input_valid_cpython(ghenv, thickness, "Thickness"):
            return

        if not config_set:
            config_set = [None]

        scene = Scene()
        containers = []
        # check list lengths for consistency
        N = len(surface)
        if len(thickness) not in (1, N):
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, " In 'T' I need either one or the same number of inputs as the Crv parameter.")

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
