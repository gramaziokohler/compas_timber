from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class ShowAssembly(component):
    def RunScript(self, assembly, show_features):

        if not assembly:
            self.AddRuntimeMessage(Warning, "Input parameter assembly failed to collect data")
            return
        assembly = assembly.copy()  # we're gonna be making changes to upstream objects

        geometry = []
        errors = []
        for beam in assembly.beams:
            if show_features:
                errors.extend(beam.apply_features())
            geometry.append(beam.get_geometry(True).native_brep)

        return geometry, errors
