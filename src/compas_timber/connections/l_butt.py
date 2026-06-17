from typing import Optional

from compas.geometry import Plane

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy

from .butt_joint import ButtJoint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
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
        :meth:`back_plane_args` to compute these from a world-coordinate plane and pass the result as keyword arguments.
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
        """The plane used to cut the cross beam when `modify_cross` is True.

        Computed from `back_plane_ref_side_index`/`back_plane_angle`/`back_plane_offset`. If no override is set, defaults
        to the side of the main beam opposite the cross beam (same as `ButtJoint._back_cutting_plane`).
        """
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

    @classmethod
    def create(cls, model, main_beam=None, cross_beam=None, small_beam_butts=False, **kwargs):
        if small_beam_butts:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam
        joint = cls(main_beam, cross_beam, **kwargs)
        model.add_joint(joint)
        return joint

    @staticmethod
    def back_plane_args(main_beam, cross_beam, back_plane: Plane) -> dict:
        """Returns kwargs encoding `back_plane` (world coordinates) as `back_plane_ref_side_index`/`back_plane_angle`/`back_plane_offset`.

        Pass the returned dict as keyword arguments to :meth:`~compas_timber.connections.Joint.create`.

        Parameters
        ----------
        main_beam : :class:`~compas_timber.elements.Beam`
        cross_beam : :class:`~compas_timber.elements.Beam`
        back_plane : :class:`~compas.geometry.Plane`
            A plane in world coordinates used to cut the cross beam. Must be parallel to the main beam's centerline
            (normal perpendicular to the main beam's length direction).

        Returns
        -------
        dict
            Keys: ``back_plane_ref_side_index``, ``back_plane_angle``, ``back_plane_offset``.

        """
        ref_side_dict = beam_ref_side_incidence(cross_beam, main_beam, ignore_ends=True)
        main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        ref_side_index = (main_beam_ref_side_index + 2) % 4
        ref_side = main_beam.ref_sides[ref_side_index]
        angle, offset = decompose_plane_to_ref_side(ref_side, back_plane, plane_name="back_plane", reference_name="main_beam")
        return {
            "back_plane_ref_side_index": ref_side_index,
            "back_plane_angle": angle,
            "back_plane_offset": offset,
        }
