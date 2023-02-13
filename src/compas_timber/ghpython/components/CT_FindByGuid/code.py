from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByRhinoGuid(component):
    def RunScript(self, Beams, Guids):
        if not (Beams and Guids):
            return

        if not isinstance(Guids, list):
            Guids = [Guids]
        Guids = [str(g) for g in Guids]
        FoundBeams = []
        for beam in Beams:
            if beam.attributes.get("rhino_guid", None) in Guids:
                FoundBeams.append(beam)

        if not FoundBeams:
            self.AddRuntimeMessage(Warning, "No beams found!")

        return FoundBeams
