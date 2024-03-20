from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.data import json_load
from compas.scene import Scene
from compas_timber.consumers import BrepGeometryConsumer

from scriptcontext import sticky

class ImportTimberAssembly(component):

    def RunScript(self, filepath, import_):
        if not filepath:
            self.AddRuntimeMessage(Warning, "Input parameter Filepath failed to collect data")

        KEY = "assembly"
        if import_:
            sticky[KEY] = json_load(filepath)
        scene = Scene()
        assembly = sticky.get(KEY, None)
        if assembly:
            consumer = BrepGeometryConsumer(assembly)
            for result in consumer.result:
                scene.add(result.geometry)

        return assembly, scene.draw()
