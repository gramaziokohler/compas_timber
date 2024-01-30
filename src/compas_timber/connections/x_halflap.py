from compas.geometry import Frame
from compas_timber.parts import MillVolume
from compas_timber.connections.lap_joint import LapJoint
from compas_timber.connections.joint import Joint

from .solver import JointTopology
from .joint import BeamJoinningError


class XHalfLapJoint(LapJoint):
    """Represents a X-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `XHalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(XHalfLapJoint, self).__init__(frame, key)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = beam_a.key if beam_a else None
        self.beam_b_key = beam_b.key if beam_b else None
        self.flip_lap_side = flip_lap_side  # Decide if Direction of beam_a or beam_b
        self.cut_plane_bias = cut_plane_bias
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "beam_a": self.beam_a_key,
            "beam_b": self.beam_b_key,
            "flip_lap_side": self.flip_lap_side,
            "cut_plane_bias": self.cut_plane_bias,
        }
        data_dict.update(super(XHalfLapJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(
            frame=Frame.__from_data__(value["frame"]), key=value["key"], cut_plane_bias=value["cut_plane_bias"]
        )
        instance.beam_a_key = value["beam_a"]
        instance.beam_b_key = value["beam_b"]
        instance.flip_lap_side = value["flip_lap_side"]
        instance.cut_plane_bias = value["cut_plane_bias"]
        return instance

    @property
    def joint_type(self):
        return "X-HalfLap"

    @property
    def beams(self):
        return [self.beam_a, self.beam_b]

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)

    def add_features(self):
        assert self.beam_a and self.beam_b  # should never happen

        try:
            negative_brep_beam_a, negative_brep_beam_b = self._create_negative_volumes()
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        self.beam_a.add_features(MillVolume(negative_brep_beam_a))
        self.beam_b.add_features(MillVolume(negative_brep_beam_b))
