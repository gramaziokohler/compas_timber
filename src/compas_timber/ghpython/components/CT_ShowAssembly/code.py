from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.artists import Artist


class ShowAssembly(component):
    def RunScript(self, Assembly, showFeatures):
        if not Assembly:
            self.AddRuntimeMessage(Warning, "Input parameter Assembly failed to collect data")
            return
        Assembly = Assembly.copy()  # we're gonna be making changes to upstream objects

        Geometry = []
        Errors = []
        for beam in Assembly.beams:
            if showFeatures:
                Errors.extend(beam.apply_features())
            brep = beam.get_geometry(showFeatures)
            Geometry.append(Artist(brep).draw())

        return Geometry, Errors
