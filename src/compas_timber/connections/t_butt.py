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
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, **kwargs):
        super(TButtJoint, self).__init__(main_beam, cross_beam, mill_depth, **kwargs)

    def get_cutting_plane(self):
        assert self.main_beam and self.cross_beam  # should never happen

        _, cfr = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam)
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr

    def restore_beams_from_keys(self, model):
        """After de-serialization, resotres references to the main and cross beams saved in the model."""
        self.main_beam = model.elementdict[self.main_beam_key]
        self.cross_beam = model.elementdict[self.cross_beam_key]

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
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.guid)

        trim_feature = CutFeature(cutting_plane)
        if self.mill_depth:
            self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        self.main_beam.add_features(trim_feature)
        self.features = [trim_feature]
