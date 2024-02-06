from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.scene import Scene


class MyComponent(component):

    def RunScript(self, trajectory):
        scene = Scene()

        for beam in trajectory.attributes.get("beams_in_scene"):
            scene.add(beam.blank)

        a = scene.draw()

        return a
