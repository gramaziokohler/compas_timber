from compas_timber.connections import LMiterJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut


class LMiterFactory(object):
    """
    Factory class for creating L-Miter joints.
    """

    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        """
        Apply processings to the parts involved in the L-Miter joint.

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
        beams = [joint.beam_a, joint.beam_b]
        parts[str(beams[0].key)].processings.append(
            BTLxJackCut.create_process(parts[str(beams[0].key)], joint.get_cutting_planes()[0], "L-Miter Joint")
        )
        parts[str(beams[1].key)].processings.append(
            BTLxJackCut.create_process(parts[str(beams[1].key)], joint.get_cutting_planes()[1], "L-Miter Joint")
        )


BTLx.register_joint(LMiterJoint, LMiterFactory)
