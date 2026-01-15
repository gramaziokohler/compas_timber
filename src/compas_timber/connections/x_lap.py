from compas_timber.fabrication import LapProxy

from .lap_joint import LapJoint
from .solver import JointTopology


class XLapJoint(LapJoint):
    """Represents an X-Lap type joint which joins the two beams somewhere along their length with a lap.

    This joint type is compatible with beams in X topology.

    Please use `XLapJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
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
        negative_volume_main, negative_volume_cross = self._create_negative_volumes(self.cut_plane_bias)

        main_lap_feature = LapProxy.from_volume_and_beam(negative_volume_main, self.beam_a, ref_side_index=self.ref_side_index_a)
        cross_lap_feature = LapProxy.from_volume_and_beam(negative_volume_cross, self.beam_b, ref_side_index=self.ref_side_index_b)

        # add features to the beams
        self.beam_a.add_features(main_lap_feature)
        self.beam_b.add_features(cross_lap_feature)

        # register processings to the joint
        self.features.extend([main_lap_feature, cross_lap_feature])
