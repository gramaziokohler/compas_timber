from compas_timber.elements import MillVolume

from compas_timber.errors import BeamJoinningError
from .lap_joint import LapJoint
from .solver import JointTopology


class XHalfLapJoint(LapJoint):
    """Represents a X-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `XHalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(XHalfLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)

    def add_features(self):
        assert self.main_beam and self.cross_beam  # should never happen

        try:
            negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
        volume_a = MillVolume(negative_brep_beam_a)
        volume_b = MillVolume(negative_brep_beam_b)
        self.main_beam.add_features(volume_a)
        self.cross_beam.add_features(volume_b)
        self.features = [volume_a, volume_b]
