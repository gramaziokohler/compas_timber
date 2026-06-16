from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy

from .butt_joint import ButtJoint
from .solver import JointTopology
from .utilities import decompose_plane_to_ref_side
from .utilities import plane_from_ref_side_angle_offset


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
        The depth of the pocket to be milled in the cross beam. This will be ignored if `butt_plane_ref_side_index` is set.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane_ref_side_index : int, optional
        The index of the cross beam's reference side that the user-defined `butt_plane` is anchored on. This is normally not
        set directly: use :meth:`create` with a `butt_plane` argument instead.
    butt_plane_angle : float, optional
        Rotation angle, in radians, of `butt_plane` around the x-axis of the reference side at `butt_plane_ref_side_index`.
    butt_plane_offset : float, optional
        Signed distance, along the (rotated) normal, from the reference side at `butt_plane_ref_side_index` to `butt_plane`.
    back_plane_ref_side_index : int, optional
        The index of the main beam's reference side that the user-defined `back_plane` is anchored on. This is normally not
        set directly: use :meth:`create` with a `back_plane` argument instead.
    back_plane_angle : float, optional
        Rotation angle, in radians, of `back_plane` around the x-axis of the reference side at `back_plane_ref_side_index`.
    back_plane_offset : float, optional
        Signed distance, along the (rotated) normal, from the reference side at `back_plane_ref_side_index` to `back_plane`.
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
        data["back_plane_ref_side_index"] = self.back_plane_ref_side_index
        data["back_plane_angle"] = self.back_plane_angle
        data["back_plane_offset"] = self.back_plane_offset
        data["reject_i"] = self.reject_i
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=None,
        modify_cross=True,
        reject_i=False,
        butt_plane_ref_side_index=None,
        butt_plane_angle=None,
        butt_plane_offset=None,
        back_plane_ref_side_index=None,
        back_plane_angle=None,
        back_plane_offset=None,
        **kwargs,
    ):
        super(LButtJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            modify_cross=modify_cross,
            butt_plane_ref_side_index=butt_plane_ref_side_index,
            butt_plane_angle=butt_plane_angle,
            butt_plane_offset=butt_plane_offset,
            **kwargs,
        )
        self.reject_i = reject_i
        self.back_plane_ref_side_index = back_plane_ref_side_index
        self.back_plane_angle = back_plane_angle if back_plane_angle is not None else 0.0
        self.back_plane_offset = back_plane_offset if back_plane_offset is not None else 0.0

    @property
    def back_plane(self):
        if self.back_plane_ref_side_index is None:
            return None
        ref_side = self.main_beam.ref_sides[self.back_plane_ref_side_index]
        return plane_from_ref_side_angle_offset(ref_side, self.back_plane_angle, self.back_plane_offset)

    @property
    def main_beam_ref_side_index(self):
        ref_side_index = super(LButtJoint, self).main_beam_ref_side_index

        beam_meet_at_ends = ref_side_index in (4, 5)

        if self.reject_i and beam_meet_at_ends:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Beams are in I topology and reject_i flag is True")

        return ref_side_index

    @classmethod
    def create(
        cls, model, main_beam=None, cross_beam=None, mill_depth=None, small_beam_butts=False, modify_cross=True, reject_i=False, butt_plane=None, back_plane=None, **kwargs
    ):
        """Creates an instance of this joint and adds it to the model.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joint belong.
        main_beam : :class:`~compas_timber.elements.Beam`
            The main beam to be joined.
        cross_beam : :class:`~compas_timber.elements.Beam`
            The cross beam to be joined.
        mill_depth : float, optional
            The depth of the pocket to be milled in the cross beam.
        small_beam_butts : bool, optional
            If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
        modify_cross : bool, optional
            If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
        reject_i : bool, optional
            If True, the joint will reject beams in I topology.
        butt_plane : :class:`~compas.geometry.Plane`, optional
            A user-defined plane, in world coordinates, used to cut the main beam instead of the closest side of the cross
            beam. Must be parallel to the cross beam's centerline. Internally decomposed into a ref_side_index/angle/offset
            anchored on the cross beam's side closest to the main beam, so it keeps tracking the beams' current geometry.
        back_plane : :class:`~compas.geometry.Plane`, optional
            A user-defined plane, in world coordinates, used to cut the cross beam instead of the back side of the main
            beam. Must be parallel to the main beam's centerline. Internally decomposed into a ref_side_index/angle/offset
            anchored on the main beam's side opposite the cross beam, so it keeps tracking the beams' current geometry.
        **kwargs : dict
            Additional keyword arguments passed to the joint's constructor.

        Returns
        -------
        :class:`~compas_timber.connections.LButtJoint`

        """
        if small_beam_butts:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam

        joint = cls(
            main_beam,
            cross_beam,
            mill_depth=mill_depth,
            modify_cross=modify_cross,
            reject_i=reject_i,
            **kwargs,
        )
        if butt_plane is not None:
            ref_side = cross_beam.ref_sides[joint.cross_beam_ref_side_index]
            angle, offset = decompose_plane_to_ref_side(ref_side, butt_plane, plane_name="butt_plane", reference_name="cross_beam")
            joint.butt_plane_ref_side_index = joint.cross_beam_ref_side_index
            joint.butt_plane_angle = angle
            joint.butt_plane_offset = offset
        if back_plane is not None:
            back_ref_side_index = (joint.main_beam_ref_side_index + 2) % 4
            ref_side = main_beam.ref_sides[back_ref_side_index]
            angle, offset = decompose_plane_to_ref_side(ref_side, back_plane, plane_name="back_plane", reference_name="main_beam")
            joint.back_plane_ref_side_index = back_ref_side_index
            joint.back_plane_angle = angle
            joint.back_plane_offset = offset
        model.add_joint(joint)
        return joint

    def add_features(self) -> None:
        """Removes this joint's previously generated features and adds new features to each beam."""
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)
        # get the cutting plane for the main beam
        if self.butt_plane:
            cutting_plane = self.butt_plane
        else:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            cutting_plane.xaxis = -cutting_plane.xaxis
            if self.mill_depth:
                cutting_plane.translate(cutting_plane.normal * self.mill_depth)
        # apply the cut on the main beam
        main_feature = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.main_beam, self.main_beam_ref_side_index)
        self.main_beam.add_features(main_feature)
        # store the feature
        self.features = [main_feature]

        if self.force_pocket:
            self._apply_pocket_to_cross_beam()
        else:
            self._apply_lap_to_cross_beam()
        # apply a refinement cut on the cross beam
        if self.modify_cross:
            if self.back_plane:
                modification_plane = self.back_plane
            else:
                modification_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
            cross_refinement_feature = JackRafterCutProxy.from_plane_and_beam(modification_plane, self.cross_beam, self.cross_beam_ref_side_index)
            self.cross_beam.add_features(cross_refinement_feature)
            self.features.append(cross_refinement_feature)
