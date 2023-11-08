from compas_timber.fabrication import BTLx
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLxFrenchRidgeLap


class FrenchRidgeFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processings(self, joint, parts):
        top_key = joint.beams[0].key
        top_part = parts[str(top_key)]
        top_part._test.append(
            top_part.reference_surfaces[str(joint.reference_face_indices[str(top_part.beam.key)])]
        )
        top_part.processings.append(BTLxFrenchRidgeLap.create_process(top_part, joint, True))

        bottom_key  = joint.beams[1].key
        bottom_part = parts[str(bottom_key)]
        bottom_part._test.append(
            bottom_part.reference_surfaces[str(joint.reference_face_indices[str(bottom_part.beam.key)])]
        )
        bottom_part.processings.append(BTLxFrenchRidgeLap.create_process(bottom_part, joint, False))


BTLx.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
