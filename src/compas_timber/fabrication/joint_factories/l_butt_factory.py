from compas_timber.connections import LButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut


class LButtFactory(object):
    """
    Factory class for creating L-Butt joints.
    """

    def __init__(self):
        pass

    @classmethod
    def apply_processings(cls, joint, parts):
        """Apply processings to the joint and its associated parts.

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

        main_part = parts[str(joint.main_beam.key)]
        cross_part = parts[str(joint.cross_beam.key)]
        main_part.processings.append(BTLxJackCut.create_process(main_part, joint.get_main_cutting_plane()[0], "L-Butt Joint"))
        cross_part.processings.append(BTLxJackCut.create_process(cross_part, joint.get_cross_cutting_plane(), "L-Butt Joint"))


BTLx.register_joint(LButtJoint, LButtFactory)
