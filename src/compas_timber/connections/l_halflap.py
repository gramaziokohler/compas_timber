from compas.geometry import Frame
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas_timber.connections.lap_joint import LapJoint

from .joint import BeamJoinningError
from .solver import JointTopology


class LHalfLapJoint(LapJoint):
    """Represents a L-Lap type joint which joins the ends of two beams,
    trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LHalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    beam_a : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    beam_a_key : str
        The key of the main beam.
    beam_b_key : str
        The key of the cross beam.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.


    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(LHalfLapJoint, self).__init__(beam_a, beam_b, flip_lap_side, cut_plane_bias, frame, key)

    @property
    def joint_type(self):
        return "L-HalfLap"

    def add_features(self):
        assert self.beam_a and self.beam_b

        try:
            main_cutting_frame = self.get_main_cutting_frame()
            cross_cutting_frame = self.get_cross_cutting_frame()
            negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        start_main, end_main = self.beam_a.extension_to_plane(main_cutting_frame)
        start_cross, end_cross = self.beam_b.extension_to_plane(cross_cutting_frame)

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.beam_a.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)
        self.beam_b.add_blank_extension(
            start_cross + extension_tolerance, end_cross + extension_tolerance, self.key
        )

        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))

        f_cross = CutFeature(cross_cutting_frame)
        self.beam_b.add_features(f_cross)
        self.features.append(f_cross)

        trim_frame = Frame(main_cutting_frame.point, main_cutting_frame.xaxis, -main_cutting_frame.yaxis)
        f_main = CutFeature(trim_frame)
        self.beam_a.add_features(f_main)
        self.features.append(f_main)
