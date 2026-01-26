from compas_timber.fabrication import LapProxy

from .lap_joint import LapJoint
from .solver import JointTopology


class XLapJoint(LapJoint):
    """Represents an X-Lap type joint which joins the two beams somewhere along their length with a lap.

    This joint type is compatible with beams in X topology.

    Please use `XLapJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        # create lap features
        negative_volume_a, negative_volume_b = self._create_negative_volumes(self.cut_plane_bias)

        lap_feature_a = LapProxy.from_volume_and_beam(negative_volume_a, self.beam_a, ref_side_index=self.ref_side_index_a)
        lap_feature_b = LapProxy.from_volume_and_beam(negative_volume_b, self.beam_b, ref_side_index=self.ref_side_index_b)

        # add features to the beams
        self.beam_a.add_features(lap_feature_a)
        self.beam_b.add_features(lap_feature_b)

        # register processings to the joint
        self.features.extend([lap_feature_a, lap_feature_b])
