from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByRhinoGuid(component):
    def RunScript(self, beams, Guid):
        if not (beams and Guid):
            return

        if not isinstance(Guid, list):
            Guid = [Guid]
        Guid = [str(g) for g in Guid]
        FoundBeam = []
        for beam in beams:
            if beam.attributes.get("rhino_guid", None) in Guid:
                FoundBeam.append(beam)

        if not FoundBeam:
            self.AddRuntimeMessage(Warning, "No beams found!")

        return FoundBeam
