from compas_timber.connections import LButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication import BTLxLap


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
        main_part.processings.append(
            BTLxJackCut.create_process(main_part, joint.get_main_cutting_plane()[0], "L-Butt Joint")
        )
        cross_part.processings.append(
            BTLxJackCut.create_process(cross_part, joint.get_cross_cutting_plane(), "L-Butt Joint")
        )
        if joint.mill_depth > 0:
            ref_face = cross_part.beam.faces[joint.reference_side_index_cross]
            joint.btlx_params_cross["reference_plane_id"] = str(cross_part.reference_surface_from_beam_face(ref_face))
            print("ref ID", joint.btlx_params_cross["reference_plane_id"])
            if joint.ends[str(cross_part.key)] == "start":
                joint.btlx_params_cross["machining_limits"] = {
                    "FaceLimitedStart": "no",
                    "FaceLimitedFront": "no",
                    "FaceLimitedBack": "no",
                }
            else:
                joint.btlx_params_cross["machining_limits"] = {
                    "FaceLimitedEnd": "no",
                    "FaceLimitedFront": "no",
                    "FaceLimitedBack": "no",
                }
            cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_cross, "L-Butt Joint"))


BTLx.register_joint(LButtJoint, LButtFactory)
