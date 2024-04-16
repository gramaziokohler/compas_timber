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
        cutting_planes = joint.get_cutting_planes()
        print("joint.beams: ", joint.beams)

        part_a, part_b = parts[str(joint.beam_a.key)], parts[str(joint.beam_b.key)]
        part_a.processings.append(
            BTLxJackCut.create_process(part_a, cutting_planes[0], "L-Miter Joint")
        )
        part_b.processings.append(
            BTLxJackCut.create_process(part_b, cutting_planes[1], "L-Miter Joint")
        )


BTLx.register_joint(LMiterJoint, LMiterFactory)
