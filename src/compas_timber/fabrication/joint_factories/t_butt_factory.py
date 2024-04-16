from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut


class TButtFactory(object):
    """Factory class for creating T-Butt joints."""

    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        """
        Apply processings to the joint and its associated parts.

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

        part = parts[str(joint.main_beam.key)]
        cut_plane = joint.get_main_cutting_plane()[0]
        part.processings.append(BTLxJackCut.create_process(part, cut_plane, "T-Butt Joint"))


BTLx.register_joint(TButtJoint, TButtFactory)
