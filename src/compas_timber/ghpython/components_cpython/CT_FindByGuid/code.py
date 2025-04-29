# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System


class FindBeamByRhinoGuid(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, beams: System.Collections.Generic.List[object], guid: System.Collections.Generic.List[System.Guid]):
        if not (beams and guid):
            return

        if not isinstance(guid, list):
            guid = [guid]
        Guid = [str(g) for g in Guid]
        FoundBeam = []
        for beam in beams:
            if beam.attributes.get("rhino_guid", None) in Guid:
                FoundBeam.append(beam)

        if not FoundBeam:
            self.AddRuntimeMessage(Warning, "No beams found!")

        return FoundBeam
