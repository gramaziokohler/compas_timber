from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import LapProxy

from .lap_joint import LapJoint
from .solver import JointTopology


class LLapJoint(LapJoint):
    """Represents an L-Lap type joint which joins the ends of two beams with a lap.

    This joint type is compatible with beams in L topology.

    Please use `LLapJoint.create()` to properly create an instance of this class and associate it with a model.

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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b

        start_a, start_b = None, None
        try:
            start_a, end_a = self.beam_a.extension_to_plane(self.cutting_plane_a)
            start_b, end_b = self.beam_b.extension_to_plane(self.cutting_plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cutting_plane_b] if start_a is not None else [self.cutting_plane_a]
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        tol = TOL.absolute
        self.beam_a.add_blank_extension(start_a + tol, end_a + tol, self.guid)
        self.beam_b.add_blank_extension(start_b + tol, end_b + tol, self.guid)

    def add_features(self):
        """Adds the required joint features to both beams."""
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        # create lap features
        negative_volume_a, negative_volume_b = self._create_negative_volumes(self.cut_plane_bias)
        lap_feature_a = LapProxy.from_volume_and_beam(negative_volume_a, self.beam_a, ref_side_index=self.ref_side_index_a)
        lap_feature_b = LapProxy.from_volume_and_beam(negative_volume_b, self.beam_b, ref_side_index=self.ref_side_index_b)

        # create cutoff features
        cut_feature_a = JackRafterCutProxy.from_plane_and_beam(self.cutting_plane_a, self.beam_a)
        cut_feature_b = JackRafterCutProxy.from_plane_and_beam(self.cutting_plane_b, self.beam_b)

        features_a = [cut_feature_a, lap_feature_a]
        features_b = [cut_feature_b, lap_feature_b]

        # add processings to beams
        self.beam_a.add_features(features_a)
        self.beam_b.add_features(features_b)

        # register processings to the joint
        self.features.extend(features_a + features_b)
