from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.assembly import TimberAssembly


class Assembly(component):
    def __init__(self):
        # maintains relationship of old_beam.id => new_beam_obj for referencing
        # lets us modify copies of the beams while referencing them using their old identities.
        self._beam_map = {}

    def _get_copied_beams(self, old_beams):
        """For the given old_beams returns their respective copies."""
        new_beams = []
        for beam in old_beams:
            new_beams.append(self._beam_map[id(beam)])
        return new_beams

    def RunScript(self, beams, joints, features):
        assembly = TimberAssembly()

        if beams:
            self._beam_map = {}
            beams = [b for b in beams if b is not None]
            for beam in beams:
                c_beam = beam.copy()
                assembly.add_beam(c_beam)
                self._beam_map[id(beam)] = c_beam
            beams = assembly.beams

        if joints:
            handled_beams = []
            joints = [j for j in joints if j is not None]
            # apply reversed. later joints in orginal list override ealier ones
            for joint in joints[::-1]:
                beams_to_pair = self._get_copied_beams(joint.beams)
                beam_pair_ids = set([id(beam) for beam in beams_to_pair])
                if beam_pair_ids in handled_beams:
                    continue
                joint.joint_type.create(assembly, *beams_to_pair)
                handled_beams.append(beam_pair_ids)

        if features:
            features = [f for f in features if f is not None]
            for f_def in features:
                beams_to_modify = self._get_copied_beams(f_def.beams)
                for beam in beams_to_modify:
                    print(beam.features)
                    beam.add_feature(f_def.feature)

        return assembly
