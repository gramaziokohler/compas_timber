from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.artists import Artist

class ShowAssembly(component):

    def RunScript(self, assembly, show_features):

        if not assembly:
            self.AddRuntimeMessage(Warning, "Input parameter assembly failed to collect data")
            return
        assembly = assembly.copy()  # we're gonna be making changes to upstream objects

        geometry = []
        for beam in assembly.beams:
            if show_features:
                beam.apply_features()
            brep = beam.get_geometry(show_features)
            geometry.append(Artist(brep).draw())

        return geometry
