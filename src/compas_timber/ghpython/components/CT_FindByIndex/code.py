from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByBeamIndex(component):
    def RunScript(self, Beams, indices):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not indices:
            self.AddRuntimeMessage(Warning, "Input parameter indices failed to collect data")
        if not (Beams and indices):
            return

        if not isinstance(indices, list):
            indices = [indices]
        indices = [int(i) for i in indices]

        FoundBeams = []
        for index in indices:
            try:
                FoundBeams.append(Beams[index])
            except IndexError:
                pass
        if not FoundBeams:
            self.AddRuntimeMessage(Warning, "No objects found!")

        return FoundBeams
