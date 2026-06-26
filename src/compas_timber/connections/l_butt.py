from typing import Optional

from compas.geometry import Plane

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy

from .butt_joint import ButtJoint
from .butt_joint import CutPlaneSpec
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
        The depth of the pocket to be milled in the cross beam. This will be ignored if `butt_plane_spec` is set.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane_spec : :class:`~compas_timber.connections.JointCutPlane`, optional
        Overrides the plane used to cut the main beam. Build with
        :meth:`~compas_timber.connections.JointCutPlane.from_butt_plane`.
    back_plane : :class:`~compas_timber.connections.JointCutPlane`, optional
        Overrides the plane used to cut the cross beam when `modify_cross` is True. Build with
        :meth:`~compas_timber.connections.JointCutPlane.from_back_plane`.
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
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the main beam. If not overridden, the closest side of the cross beam will be used.
    back_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the cross beam. If not overridden, the back side of the main beam will be used.
    reject_i : bool, default False
        If True, the joint will reject beams in I topology.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LButtJoint, self).__data__
        data["back_plane_spec"] = self._back_plane_spec
        data["modify_cross"] = self.modify_cross
        data["reject_i"] = self.reject_i
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=None,
        modify_cross=True,
        reject_i=False,
        butt_plane_spec: Optional[CutPlaneSpec] = None,
        back_plane_spec: Optional[CutPlaneSpec] = None,
        **kwargs,
    ):
        super(LButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, modify_cross=modify_cross, butt_plane_spec=butt_plane_spec, **kwargs)
        self.modify_cross = modify_cross
        self.reject_i = reject_i
        self._back_plane_spec: Optional[CutPlaneSpec] = back_plane_spec

    @property
    def back_plane(self) -> Plane:
        """The plane used to cut the cross beam when `modify_cross` is True.

        If a :class:`~compas_timber.connections.JointCutPlane` override is set, it is resolved against the main beam's
        back face (opposite the cross beam).  Otherwise defaults to the same plane as :meth:`ButtJoint._back_cutting_plane`.
        """
        if self._back_plane_spec is not None:
            return self._back_plane_spec.to_plane(self.main_beam)
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
    def create(cls, model, main_beam=None, cross_beam=None, small_beam_butts=False, **kwargs):
        if small_beam_butts:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam
        joint = cls(main_beam, cross_beam, **kwargs)
        model.add_joint(joint)
        return joint
