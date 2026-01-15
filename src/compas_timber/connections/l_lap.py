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
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L


    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b

        start_main, start_cross = None, None
        try:
            start_main, end_main = self.beam_a.extension_to_plane(self.cutting_plane_a)
            start_cross, end_cross = self.beam_b.extension_to_plane(self.cutting_plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cutting_plane_b] if start_main is not None else [self.cutting_plane_a]
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        tol = TOL.absolute
        self.beam_a.add_blank_extension(start_main + tol, end_main + tol, self.guid)
        self.beam_b.add_blank_extension(start_cross + tol, end_cross + tol, self.guid)

    def add_features(self):
        """Adds the required joint features to both beams.

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

        # create cutoff features
        main_cut_feature = JackRafterCutProxy.from_plane_and_beam(self.cutting_plane_a, self.beam_a)
        cross_cut_feature = JackRafterCutProxy.from_plane_and_beam(self.cutting_plane_b, self.beam_b)

        main_features = [main_cut_feature, main_lap_feature]
        cross_features = [cross_cut_feature, cross_lap_feature]

        # add processings to beams
        self.beam_a.add_features(main_features)
        self.beam_b.add_features(cross_features)

        # register processings to the joint
        self.features.extend(main_features + cross_features)
