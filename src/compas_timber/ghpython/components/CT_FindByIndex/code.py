from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByBeamIndex(component):
    def RunScript(self, Beams, Indices):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Indices:
            self.AddRuntimeMessage(Warning, "Input parameter Indices failed to collect data")
        if not (Beams and Indices):
            return

        if not isinstance(Indices, list):
            Indices = [Indices]
        Indices = [int(i) for i in Indices]

        FoundBeams = []
        for index in Indices:
            try:
                FoundBeams.append(Beams[index])
            except IndexError:
                pass
        if not FoundBeams:
            self.AddRuntimeMessage(Warning, "No objects found!")

        return FoundBeams
