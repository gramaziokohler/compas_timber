from compas.geometry import Plane

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy

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
        data["modify_cross"] = self.modify_cross
        data["back_plane"] = self.back_plane
        data["reject_i"] = self.reject_i
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=None,
        modify_cross=True,
        reject_i=False,
        butt_plane=None,
        back_plane=None,
        force_pocket=False,
        conical_tool=False,
        **kwargs,
    ):
        super(LButtJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            butt_plane=butt_plane,
            force_pocket=force_pocket,
            conical_tool=conical_tool,
            **kwargs,
        )
        self.modify_cross = modify_cross
        self._back_plane = back_plane
        self.reject_i = reject_i

    @property
    def back_plane(self):
        if self._back_plane is None:
            return Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index))
        return self._back_plane

    @property
    def main_beam_ref_side_index(self):
        ref_side_index = super(LButtJoint, self).main_beam_ref_side_index

        beam_meet_at_ends = ref_side_index in (4, 5)

        if self.reject_i and beam_meet_at_ends:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Beams are in I topology and reject_i flag is True")

        return ref_side_index

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.
        """
        super(LButtJoint, self).add_extensions()

        if self.modify_cross:
            assert self.main_beam and self.cross_beam
            try:
                start, end = self.cross_beam.extension_to_plane(self.back_plane)
                extension_tolerance = 0
                joint_id = self.guid
                self.cross_beam.add_blank_extension(start + extension_tolerance, end + extension_tolerance, joint_id)
            except AttributeError as ae:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[self.back_plane])

    def add_features(self):
        """Removes this joint's previously generated features and adds new features to each beam."""
        super(LButtJoint, self).add_features()

        if self.modify_cross:
            cross_refinement_feature = JackRafterCutProxy.from_plane_and_beam(self.back_plane, self.cross_beam, self.cross_beam_ref_side_index)
            self.cross_beam.add_features(cross_refinement_feature)
            self.features.append(cross_refinement_feature)

    @classmethod
    def create(
        cls, model, main_beam=None, cross_beam=None, mill_depth=None, small_beam_butts=False, modify_cross=True, reject_i=False, butt_plane=None, back_plane=None, **kwargs
    ):
        if small_beam_butts:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam
        joint = cls(main_beam, cross_beam, mill_depth, modify_cross, reject_i, butt_plane, back_plane, **kwargs)
        model.add_joint(joint)
        return joint
