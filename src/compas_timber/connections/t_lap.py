from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap

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
        assert self.main_beam and self.cross_beam
        try:
            start_main, end_main = self.main_beam.extension_to_plane(self.main_cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(
                beams=self.elements,
                joint=self,
                debug_info=str(ae),
                debug_geometries=[self.main_cutting_plane],
            )
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
            self.guid,
        )

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # create lap features
        negative_volume_main, negative_volume_cross = self._create_negative_volumes()
        main_lap_feature = Lap.from_volume_and_beam(negative_volume_main, self.main_beam, ref_side_index=self.main_ref_side_index)
        cross_lap_feature = Lap.from_volume_and_beam(negative_volume_cross, self.cross_beam, ref_side_index=self.cross_ref_side_index)

        # cutoff feature for main beam
        main_cut_feature = JackRafterCut.from_plane_and_beam(self.main_cutting_plane, self.main_beam)

        # add processings to the beams
        self.cross_beam.add_feature(cross_lap_feature)
        self.main_beam.add_features([main_lap_feature, main_cut_feature])

        # register processings to the joint
        self.features.extend([cross_lap_feature, main_lap_feature, main_cut_feature])
