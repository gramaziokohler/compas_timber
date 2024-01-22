from compas.geometry import Frame

from compas_timber.parts import CutFeature

from .joint import Joint
from .joint import beam_side_incidence
from .solver import JointTopology


class TButtJoint(Joint):
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

    def __init__(self, main_beam=None, cross_beam=None, gap=None, frame=None, key=None):
        super(TButtJoint, self).__init__(frame, key)
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.gap = gap
        self.features = []

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "gap": self.gap,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], gap=value["gap"])
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def joint_type(self):
        return "T-Butt"

    @property
    def cutting_plane(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = min(angles_faces, key=lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr

    def restore_beams_from_keys(self, assembly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assembly.find_by_key(self.main_beam_key)
        self.cross_beam = assembly.find_by_key(self.cross_beam_key)

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam).

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        if self.features:
            self.main_beam.remove_features(self.features)

        trim_feature = CutFeature(self.cutting_plane)
        self.main_beam.add_features(trim_feature)
        self.features = [trim_feature]
