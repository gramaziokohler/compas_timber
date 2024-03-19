from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication.btlx_processes.lap import BTLxLap


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

        main_part = parts[str(joint.main_beam.key)]
        cut_plane = joint.get_main_cutting_plane()[0]
        main_part.processings.append(BTLxJackCut.create_process(main_part, cut_plane, "T-Butt Joint"))

        cross_part = parts[str(joint.cross_beam.key)]
        cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_cross, "T-Butt Joint"))







BTLx.register_joint(TButtJoint, TButtFactory)


