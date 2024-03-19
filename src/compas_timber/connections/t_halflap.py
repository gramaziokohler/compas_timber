from compas.geometry import Frame

from compas_timber.connections.lap_joint import LapJoint
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume

from .joint import BeamJoinningError
from .solver import JointTopology


class THalfLapJoint(LapJoint):
    """Represents a T-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `THalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(THalfLapJoint, self).__init__(beam_a, beam_b, flip_lap_side, cut_plane_bias, frame, key)

    @property
    def joint_type(self):
        return "T-HalfLap"

    def add_features(self):
        assert self.beam_a and self.beam_b  # should never happen

        main_cutting_frame = None
        try:
            main_cutting_frame = self.get_main_cutting_frame()
            negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
            start_main, end_main = self.beam_a.extension_to_plane(main_cutting_frame)
        except AttributeError as ae:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[main_cutting_frame]
            )
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.beam_a.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))

        trim_frame = Frame(main_cutting_frame.point, main_cutting_frame.xaxis, -main_cutting_frame.yaxis)
        f_main = CutFeature(trim_frame)
        self.beam_a.add_features(f_main)
        self.features.append(f_main)
