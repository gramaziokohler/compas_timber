from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByBeamIndex(component):
    def RunScript(self, Beams, index):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not index:
            self.AddRuntimeMessage(Warning, "Input parameter indices failed to collect data")
        if not (Beams and index):
            return

        if not isinstance(index, list):
            index = [index]
        index = [int(i) for i in index]

        FoundBeam = []
        for i in index:
            try:
                FoundBeam.append(Beams[i])
            except IndexError:
                pass
        if not FoundBeam:
            self.AddRuntimeMessage(Warning, "No objects found!")

        return FoundBeam
