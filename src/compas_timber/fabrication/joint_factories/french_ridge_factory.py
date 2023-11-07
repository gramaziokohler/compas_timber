from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxFrenchRidgeLap


class FrenchRidgeFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(self, joint, parts):
        top_key = joint.beams[0].key
        top_part = parts[str(top_key)]
        top_end = joint.ends[top_key]
        top_part._test.append(
            top_part.reference_surfaces[str(joint.joint.reference_face_indices[str(top_part.beam.key)])]
        )
        top_part.processings.append(BTLxFrenchRidgeLap.create_process(top_part, joint, True, top_end))

        bottom_key, bottom_part = joint.parts.items()[1]
        bottom_end = joint.ends[bottom_key]
        bottom_part._test.append(
            bottom_part.reference_surfaces[str(joint.joint.reference_face_indices[str(bottom_part.beam.key)])]
        )
        BTLxFrenchRidgeLap.apply_process(bottom_part, joint, False, bottom_end)


BTLxJoint.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
