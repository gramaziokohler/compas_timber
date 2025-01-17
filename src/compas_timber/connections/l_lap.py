from compas.geometry import Frame

from compas_timber.elements.features import CutFeature
from compas_timber.elements.features import MillVolume
from compas_timber.errors import BeamJoinningError
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap

from .lap_joint import LapJoint
from .solver import JointTopology
from .utilities import are_beams_coplanar


class LLapJoint(LapJoint):
    """Represents an L-Lap type joint which joins the ends of two beams with a lap.

    This joint type is compatible with beams in L topology.

    Please use `LLapJoint.create()` to properly create an instance of this class and associate it with a model.

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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(LLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam

        start_main, start_cross = None, None
        try:
            start_main, end_main = self.main_beam.extension_to_plane(self.main_cutting_plane)
            start_cross, end_cross = self.cross_beam.extension_to_plane(self.cross_cutting_plane)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cross_cutting_plane] if start_main is not None else [self.main_cutting_plane]
            raise BeamJoinningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_main, end_main, self.main_beam_guid)
        self.cross_beam.add_blank_extension(start_cross, end_cross, self.cross_beam_guid)

    def add_features(self):
        """Adds the required joint features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        if are_beams_coplanar(self.elements):  # TODO: this is a temporal solution to allow the vizualization of non-coplanar lap joints.
            # calculate the lap length and depth for each beam
            main_lap_length, cross_lap_length = self._get_lap_lengths()
            main_lap_depth, cross_lap_depth = self._get_lap_depths()

            ## main_beam
            # lap feature on main_beam
            main_lap_feature = Lap.from_plane_and_beam(
                self.main_cutting_plane,
                self.main_beam,
                main_lap_length,
                main_lap_depth,
                ref_side_index=self.main_ref_side_index,
            )
            # cutoff feature for main_beam
            main_cut_feature = JackRafterCut.from_plane_and_beam(self.main_cutting_plane, self.main_beam)
            main_features = [main_cut_feature, main_lap_feature]
            self.main_beam.add_features(main_features)
            self.features.extend(main_features)

            ## cross_beam
            # lap feature on cross_beam
            cross_lap_feature = Lap.from_plane_and_beam(
                self.cross_cutting_plane,
                self.cross_beam,
                cross_lap_length,
                cross_lap_depth,
                ref_side_index=self.cross_ref_side_index,
            )
            # cutoff feature for beam_b
            cross_cut_feature = JackRafterCut.from_plane_and_beam(self.cross_cutting_plane, self.cross_beam)
            cross_features = [cross_cut_feature, cross_lap_feature]
            self.cross_beam.add_features(cross_features)
            self.features.extend(cross_features)

        else:
            # TODO: this is a temporal solution to avoid the error if beams are not coplanar and allow the visualization of the joint.
            # TODO: this solution does not generate machining features and therefore will be ignored in the fabrication process.
            # TODO: once the Lap BTLx processing implimentation allows for non-coplanar beams, this should be removed.
            try:
                main_cutting_frame = self.get_main_cutting_frame()
                cross_cutting_frame = self.get_cross_cutting_frame()
                negative_brep_main_beam, negative_brep_cross_beam = self._create_negative_volumes()
            except Exception as ex:
                raise BeamJoinningError(beams=self.elements, joint=self, debug_info=str(ex))

            main_volume = MillVolume(negative_brep_main_beam)
            cross_volume = MillVolume(negative_brep_cross_beam)

            self.main_beam.add_features(main_volume)
            self.cross_beam.add_features(cross_volume)

            f_cross = CutFeature(cross_cutting_frame)
            self.cross_beam.add_features(f_cross)

            trim_frame = Frame(main_cutting_frame.point, main_cutting_frame.xaxis, -main_cutting_frame.yaxis)
            f_main = CutFeature(trim_frame)
            self.main_beam.add_features(f_main)

            self.features = [main_volume, cross_volume, f_main, f_cross]
