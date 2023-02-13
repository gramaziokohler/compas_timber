from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByIndex(component):
    def RunScript(self, beams, indices):
        if not beams:
            self.AddRuntimeMessage(Warning, "Input parameter beams failed to collect data")
        if not indices:
            self.AddRuntimeMessage(Warning, "Input parameter indices failed to collect data")
        if not (beams and indices):
            return

        if not isinstance(indices, list):
            indices = [indices]
        indices = [int(i) for i in indices]

        found_beams = []
        for index in indices:
            try:
                found_beams.append(beams[index])
            except IndexError:
                pass
        if not found_beams:
            self.AddRuntimeMessage(Warning, "No objects found!")

        return found_beams
