from compas_timber.errors import BeamJoiningError

from .butt_joint import ButtJoint
from .solver import JointTopology


class LButtJoint(ButtJoint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam. This will be ignored if `butt_plane` is provided.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    back_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the cross beam. If not provided, the back side of the main beam will be used.
    reject_i : bool, default False
        If True, the joint will reject beams in I topology.


    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    back_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the cross beam. If not provided, the back side of the main beam will be used.
    reject_i : bool, default False
        If True, the joint will reject beams in I topology.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LButtJoint, self).__data__
        data["small_beam_butts"] = self.small_beam_butts
        data["back_plane"] = self.back_plane
        data["reject_i"] = self.reject_i
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, small_beam_butts=False, modify_cross=True, reject_i=False, butt_plane=None, back_plane=None, **kwargs):
        super(LButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, modify_cross=modify_cross, butt_plane=butt_plane, **kwargs)
        self.small_beam_butts = small_beam_butts
        self.reject_i = reject_i
        self.back_plane = back_plane
        self.update_beam_roles()

    @property
    def main_beam_ref_side_index(self):
        ref_side_index = super(LButtJoint, self).main_beam_ref_side_index

        beam_meet_at_ends = ref_side_index in (4, 5)

        if self.reject_i and beam_meet_at_ends:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Beams are in I topology and reject_i flag is True")

        return ref_side_index

    def update_beam_roles(self):
        """Flips the main and cross beams based on the joint parameters.
        Prioritizes the beam with the smaller cross-section if `small_beam_butts` is True.

        """
        if self.small_beam_butts:
            if self.main_beam.width * self.main_beam.height > self.cross_beam.width * self.cross_beam.height:
                self.main_beam, self.cross_beam = self.cross_beam, self.main_beam
                self.main_beam_guid, self.cross_beam_guid = self.cross_beam_guid, self.main_beam_guid
