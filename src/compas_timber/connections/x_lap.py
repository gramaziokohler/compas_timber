from compas_timber.elements.features import MillVolume
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import Lap

from .lap_joint import LapJoint
from .solver import JointTopology
from .utilities import are_beams_coplanar


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
    main_beam : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(XLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        if are_beams_coplanar(*self.elements):  # TODO: this is a temporal solution to allow the vizualization of non-coplanar lap joints.
            # calculate the lap length and depth for each beam
            main_lap_length, cross_lap_length = self._get_lap_lengths()
            main_lap_depth, cross_lap_depth = self._get_lap_depths()

            ## main_beam features
            # main Lap feature
            main_lap_feature = Lap.from_plane_and_beam(
                self.main_cutting_plane,
                self.main_beam,
                main_lap_length,
                main_lap_depth,
                ref_side_index=self.main_ref_side_index,
            )

            ## cross_beam features
            # cross Lap feature
            cross_lap_feature = Lap.from_plane_and_beam(
                self.cross_cutting_plane,
                self.cross_beam,
                cross_lap_length,
                cross_lap_depth,
                ref_side_index=self.cross_ref_side_index,
            )

            # add features to the beams
            self.main_beam.add_features(main_lap_feature)
            self.cross_beam.add_features(cross_lap_feature)

            # register features to the joint
            self.features.extend([main_lap_feature, cross_lap_feature])

        else:
            # TODO: this is a temporal solution to avoid the error if beams are not coplanar and allow the visualization of the joint.
            # TODO: this solution does not generate machining features and therefore will be ignored in the fabrication process.
            # TODO: once the Lap BTLx processing implimentation allows for non-coplanar beams, this should be removed.
            try:
                negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
            except Exception as ex:
                raise BeamJoiningError(beams=self.beams, joint=self, debug_info=str(ex))
            volume_a = MillVolume(negative_brep_beam_a)
            volume_b = MillVolume(negative_brep_beam_b)
            self.main_beam.add_features(volume_a)
            self.cross_beam.add_features(volume_b)
            self.features = [volume_a, volume_b]
