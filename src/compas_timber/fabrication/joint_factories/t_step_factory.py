from compas_timber.connections import TStepJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication.btlx_processes.btlx_lap import BTLxLap
from compas_timber.fabrication.btlx_processes.btlx_double_cut import BTLxDoubleCut


class TStepFactory(object):
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

        if joint.check_stepjoint_boolean():
            ref_face = main_part.beam.faces[joint.ref_face_id]
            joint.btlx_params_stepjoint_main["ReferencePlaneID"] = str(main_part.reference_surface_from_beam_face(ref_face))
            main_part.processings.append(BTLxDoubleCut.create_process(joint.btlx_params_stepjoint_main, "TStepJoint"))
            ref_face_cross = cross_part.beam.faces[joint.cross_face_id]
            joint.btlx_params_stepjoint_cross["ReferencePlaneID"] = str(cross_part.reference_surface_from_beam_face(ref_face_cross))
            cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_stepjoint_cross, "TStepJoint Pocket"))
        else:
            main_part.processings.append(BTLxJackCut.create_process(main_part, cut_plane, "TButt"))

        if joint.drill_diameter > 0:
            joint.btlx_drilling_params_cross["ReferencePlaneID"] = str(cross_part.reference_surface_from_beam_face(ref_plane))

BTLx.register_joint(TStepJoint, TStepFactory)