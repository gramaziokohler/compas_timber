from compas.geometry import Frame

from compas_timber.elements import CutFeature
from compas_timber.elements import MillVolume
from compas_timber.errors import BeamJoinningError

from .lap_joint import LapJoint
from .solver import JointTopology


class LHalfLapJoint(LapJoint):
    """Represents a L-Lap type joint which joins the ends of two beams,
    trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LHalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

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
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
        super(LHalfLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        try:
            main_cutting_frame = self.get_main_cutting_frame()
            cross_cutting_frame = self.get_cross_cutting_frame()
        except Exception as ex:
            raise BeamJoinningError(beams=self.elements, joint=self, debug_info=str(ex))

        start_main, end_main = self.main_beam.extension_to_plane(main_cutting_frame)
        start_cross, end_cross = self.cross_beam.extension_to_plane(cross_cutting_frame)

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.guid)
        self.cross_beam.add_blank_extension(
            start_cross + extension_tolerance, end_cross + extension_tolerance, self.guid
        )

    def add_features(self):
        assert self.main_beam and self.cross_beam

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
