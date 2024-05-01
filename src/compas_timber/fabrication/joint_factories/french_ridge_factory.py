from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxFrenchRidgeLap


class FrenchRidgeFactory(object):
    """
    Factory class for creating French ridge joints.
    """

    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        """
        Apply processings to the joint and parts.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint.Joint`
            The joint object.
        parts : dict
            A dictionary of the BTLxParts connected by this joint, with part keys as the dictionary keys.

        Returns
        -------
        None

        """

        top_key = joint.beams[0].key
        top_part = parts[str(top_key)]
        # top_part._test.append(top_part.reference_surface_planes(joint.reference_face_indices[str(top_part.beam.key)]))
        top_part.processings.append(BTLxFrenchRidgeLap.create_process(top_part, joint, True))

        bottom_key = joint.beams[1].key
        bottom_part = parts[str(bottom_key)]
        # bottom_part._test.append(
            # bottom_part.reference_surface_planes(joint.reference_face_indices[str(bottom_part.beam.key)])
        # )
        bottom_part.processings.append(BTLxFrenchRidgeLap.create_process(bottom_part, joint, False))


BTLx.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
