from compas.geometry import Frame
from compas_timber.connections.butt_joint import ButtJoint

from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume

from .joint import BeamJoinningError
from .solver import JointTopology


class TButtJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.TimberAssembly`
        The assembly associated with the beams to be joined.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    cutting_plane_main : :class:`~compas.geometry.Frame`
        The frame by which the main beam is trimmed.
    cutting_plane_cross : :class:`~compas.geometry.Frame`
        The frame by which the cross beam is trimmed.
    joint_type : str
        A string representation of this joint's type.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, gap=None, frame=None, key=None):
        super(TButtJoint, self).__init__(frame, key)
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.mill_depth = mill_depth
        self.gap = gap
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "mill_depth": self.mill_depth,
            "gap": self.gap,
        }
        data_dict.update(super(TButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(frame=Frame.__from_data__(value["frame"]), key=value["key"], gap=value["gap"])
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        instance.mill_depth = value["mill_depth"]
        instance.gap = value["gap"]
        return instance

    @property
    def joint_type(self):
        return "T-Butt"

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam).

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
        cutting_plane = None
        try:
            cutting_plane = self.get_main_cutting_plane()[0]
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

        trim_feature = CutFeature(cutting_plane)
        if self.mill_depth:
            self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        self.main_beam.add_features(trim_feature)
        self.features = [trim_feature]
