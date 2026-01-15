from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import LapProxy

from .lap_joint import LapJoint
from .solver import JointTopology


class TLapJoint(LapJoint):
    """Represents a T-Lap type joint which joins the end of a beam along the length of another beam with a lap.

    This joint type is compatible with beams in T topology.

    Please use `TLapJoint.create()` to properly create an instance of this class and associate it with a model.

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

    Attributes
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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TLapJoint, self).__data__
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(TLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)




    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b
        try:
            start_main, end_main = self.beam_a.extension_to_plane(self.cutting_plane_a)
        except AttributeError as ae:
            raise BeamJoiningError(
                beams=self.elements,
                joint=self,
                debug_info=str(ae),
                debug_geometries=[self.cutting_plane_a],
            )
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.beam_a.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
            self.guid,
        )

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

        # cutoff feature for main beam
        main_cut_feature = JackRafterCutProxy.from_plane_and_beam(self.cutting_plane_a, self.beam_a)

        # add processings to the beams
        self.beam_b.add_feature(cross_lap_feature)
        self.beam_a.add_features([main_lap_feature, main_cut_feature])

        # register processings to the joint
        self.features.extend([cross_lap_feature, main_lap_feature, main_cut_feature])
