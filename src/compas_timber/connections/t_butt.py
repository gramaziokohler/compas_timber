from compas.geometry import BrepTrimmingError
from compas.geometry import Frame

from compas_timber.parts import BeamTrimmingFeature

from .joint import BeamJoinningError
from .joint import Joint
from .joint import beam_side_incidence
from .solver import JointTopology


class TButtJoint(Joint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.Assembly`
        The assembly associated with the beams to be joined.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    joint_type : str
        A string representation of this joint's type.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    cutting_plane_main : :class:`~compas.geometry.Frame`
        The frame by which the main beam is trimmed.
    cutting_plane_cross : :class:`~compas.geometry.Frame`
        The frame by which the cross beam is trimmed.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
        super(TButtJoint, self).__init__(assembly, [main_beam, cross_beam])
        self.main_beam_key = None
        self.cross_beam_key = None
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.gap = None
        self.features = []

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam.key,
            "cross_beam_key": self.cross_beam.key,
            "gap": self.gap,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @data.setter
    def data(self, value):
        Joint.data.fset(self, value)
        self.main_beam_key = value["main_beam_key"]
        self.cross_beam_key = value["cross_beam_key"]
        self.gap = value["gap"]

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

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam)."""
        if self.features:
            self.main_beam.clear_features(self.features)
            self.features = []

        trim_feature = BeamTrimmingFeature(self.cutting_plane)
        try:
            self.main_beam.add_feature(trim_feature)
            self.features.append(trim_feature)
        except BrepTrimmingError:
            msg = "Failed trimming beam: {} with cutting plane: {}. Does it intersect with beam: {}".format(
                self.main_beam, self.cutting_plane, self.cross_beam
            )
            raise BeamJoinningError(msg)
