from typing import Optional

from compas.geometry import Plane

from compas_timber.errors import BeamJoiningError

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
    back_plane_ref_side_index : int, optional
        The index of the main beam's reference side that `back_plane` is anchored on. If not provided, the side of the main
        beam opposite the one facing the cross beam is used (see :attr:`back_plane`). This is normally not set directly: use
        :meth:`create` with a `back_plane` argument, which derives this together with `back_plane_angle` and
        `back_plane_offset` from a plane in world coordinates.
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
    butt_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the main beam. If not overridden, the closest side of the cross beam will be used.
    back_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the cross beam, derived from `back_plane_ref_side_index`/`back_plane_angle`/
        `back_plane_offset`. If not overridden, the back side of the main beam will be used.
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
        back_plane_ref_side_index: Optional[int] = None,
        back_plane_angle: Optional[float] = None,
        back_plane_offset: Optional[float] = None,
        **kwargs,
    ):
        super(LButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, modify_cross=modify_cross, **kwargs)
        self.reject_i = reject_i
        self.back_plane_ref_side_index: Optional[int] = back_plane_ref_side_index
        self.back_plane_angle: float = back_plane_angle if back_plane_angle is not None else 0.0
        self.back_plane_offset: float = back_plane_offset if back_plane_offset is not None else 0.0

    @property
    def back_plane(self) -> Plane:
        if self.back_plane_ref_side_index is not None:
            ref_side = self.main_beam.ref_sides[self.back_plane_ref_side_index]
            return plane_from_ref_side_angle_offset(ref_side, self.back_plane_angle, self.back_plane_offset)
        # default: the side of the main beam opposite the one facing the cross beam, same as ButtJoint's default
        return super(LButtJoint, self)._back_cutting_plane()

    def _back_cutting_plane(self) -> Plane:
        return self.back_plane

    @property
    def main_beam_ref_side_index(self):
        ref_side_index = super(LButtJoint, self).main_beam_ref_side_index

        beam_meet_at_ends = ref_side_index in (4, 5)

        if self.reject_i and beam_meet_at_ends:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Beams are in I topology and reject_i flag is True")

        return ref_side_index

    @staticmethod
    def _set_back_plane_override(joint: "LButtJoint", back_plane: Optional[Plane]) -> None:
        """Decomposes `back_plane` (world coordinates) and stores it on `joint` as a ref_side_index/angle/offset."""
        if back_plane is None:
            return
        ref_side_index = (joint.main_beam_ref_side_index + 2) % 4
        ref_side = joint.main_beam.ref_sides[ref_side_index]
        angle, offset = decompose_plane_to_ref_side(ref_side, back_plane, plane_name="back_plane", reference_name="main_beam")
        joint.back_plane_ref_side_index = ref_side_index
        joint.back_plane_angle = angle
        joint.back_plane_offset = offset

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
        cls._set_butt_plane_override(joint, butt_plane)
        cls._set_back_plane_override(joint, back_plane)
        model.add_joint(joint)
        return joint
