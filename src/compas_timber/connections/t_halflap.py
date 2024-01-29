from compas.geometry import Frame

from compas_timber.connections.lap_joint import LapJoint
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume

from .joint import Joint
from .solver import JointTopology


class THalfLapJoint(LapJoint):
    """Represents a T-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `THalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(THalfLapJoint, self).__init__(frame, key)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.flip_lap_side = flip_lap_side  # Decide if Direction of main_beam or cross_beam
        self.features = []
        self.cut_plane_bias = cut_plane_bias

    @property
    def data(self):
        data_dict = {
            "main_beam": self.main_beam_key,
            "cross_beam": self.cross_beam_key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], cutoff=value["cut_plane_choice"])
        instance.main_beam_key = value["main_beam"]
        instance.cross_beam_key = value["cross_beam"]
        instance.cut_plane_choice = value["cut_plane_choice"]
        return instance

    @property
    def joint_type(self):
        return "T-HalfLap"

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def add_features(self):
        start_main, end_main = self.main_beam.extension_to_plane(self.cutting_frame_main)
        self.main_beam.add_blank_extension(start_main, end_main, self.key)

        negative_brep_main_beam, negative_brep_cross_beam = self._create_negative_volumes()
        self.main_beam.add_features(MillVolume(negative_brep_main_beam))
        self.cross_beam.add_features(MillVolume(negative_brep_cross_beam))

        trim_frame = Frame(self.cutting_frame_main.point, self.cutting_frame_main.xaxis, -self.cutting_frame_main.yaxis)
        f_main = CutFeature(trim_frame)
        self.main_beam.add_features(f_main)
        self.features.append(f_main)
