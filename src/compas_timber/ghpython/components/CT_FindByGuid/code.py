from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


class FindBeamByRhinoGuid(component):
    def RunScript(self, beams, guids):
        if not (beams and guids):
            return

        if not isinstance(guids, list):
            guids = [guids]
        guids = [str(g) for g in guids]
        found_beams = []
        for beam in beams:
            if beam.attributes.get("rhino_guid", None) in guids:
                found_beams.append(beam)

        if not found_beams:
            self.AddRuntimeMessage(Warning, "No beams found!")

        return found_beams
