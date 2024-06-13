from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication.btlx_processes.btlx_lap import BTLxLap
from compas_timber.fabrication.btlx_processes.btlx_double_cut import BTLxDoubleCut


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

        main_part = parts[str(joint.main_beam.guid)]
        cross_part = parts[str(joint.cross_beam.guid)]
        cut_plane, ref_plane = joint.get_main_cutting_plane()

        if joint.birdsmouth:
            joint.calc_params_birdsmouth()
            ref_face = main_part.beam.faces[joint.btlx_params_main["ReferencePlaneID"]]
            joint.btlx_params_main["ReferencePlaneID"] = str(main_part.reference_surface_from_beam_face(ref_face))
            main_part.processings.append(BTLxDoubleCut.create_process(joint.btlx_params_main, "T-Butt Joint"))
        else:
            main_part.processings.append(BTLxJackCut.create_process(main_part, cut_plane, "T-Butt Joint"))

        joint.btlx_params_cross["reference_plane_id"] = cross_part.reference_surface_from_beam_face(ref_plane)
        if joint.mill_depth > 0:
            joint.btlx_params_cross["machining_limits"] = {"FaceLimitedFront": "no", "FaceLimitedBack": "no"}
            cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_cross, "T-Butt Joint"))


BTLx.register_joint(TButtJoint, TButtFactory)
