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
        data["local_back_plane"] = self.local_back_plane
        data["reject_i"] = self.reject_i
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, modify_cross=True, reject_i=False, butt_plane=None, back_plane=None, **kwargs):
        super(LButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, modify_cross=modify_cross, butt_plane=butt_plane, **kwargs)
        self.reject_i = reject_i
        self.local_back_plane = back_plane.transformed(main_beam.modeltransformation.inverse()) if back_plane else None

    @property
    def back_plane(self):
        if self.local_back_plane:
            return self.local_back_plane.transformed(self.main_beam.modeltransformation)
        return None

    @property
    def butt_plane(self):
        if self.local_butt_plane:
            return self.local_butt_plane.transformed(self.main_beam.modeltransformation)
        return None

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
        if small_beam_butts:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam
        joint = cls(main_beam, cross_beam, mill_depth, modify_cross, reject_i, butt_plane, back_plane, **kwargs)
        model.add_joint(joint)
        return joint

    @classmethod
    def __from_data__(cls, data):
        local_butt_plane = data.pop("local_butt_plane", None)
        local_back_plane = data.pop("local_back_plane", None)
        joint = cls(**data)
        joint.local_butt_plane = local_butt_plane
        joint.local_back_plane = local_back_plane
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
