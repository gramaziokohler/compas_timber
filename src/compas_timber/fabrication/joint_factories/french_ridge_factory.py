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

        top_part = parts[str(joint.beam_a.key)]
        top_part.processings.append(BTLxFrenchRidgeLap.create_process(top_part, joint, True))

        bottom_part = parts[str(joint.beam_b.key)]
        bottom_part.processings.append(BTLxFrenchRidgeLap.create_process(bottom_part, joint, False))


BTLx.register_joint(FrenchRidgeLapJoint, FrenchRidgeFactory)
