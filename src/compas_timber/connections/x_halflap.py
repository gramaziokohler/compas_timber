from compas_timber.parts import MillVolume
from compas_timber.connections import LapJoint

from .solver import JointTopology
from .joint import BeamJoinningError


class XHalfLapJoint(LapJoint):
    """Represents a X-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `XHalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    beam_a : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_key : str
        The key of the main beam.
    cross_beam_key : str
        The key of the cross beam.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.


    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(XHalfLapJoint, self).__init__(beam_a, beam_b, flip_lap_side, cut_plane_bias, frame, key)

    @property
    def joint_type(self):
        return "X-HalfLap"

    def add_features(self):
        assert self.beam_a and self.beam_b  # should never happen

        try:
            negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))
