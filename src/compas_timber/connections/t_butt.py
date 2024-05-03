from compas_timber.connections.butt_joint import ButtJoint

from compas_timber.parts import CutFeature
from compas_timber.parts import BrepSubtraction
from compas_timber.parts import MillVolume
from compas_timber.parts import DrillFeature

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

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, drill_diameter=0, birdsmouth=False, **kwargs):
        super(TButtJoint, self).__init__(main_beam, cross_beam, mill_depth, drill_diameter, birdsmouth, **kwargs)


    def add_extensions(self):
        """Adds the extensions to the main beam and cross beam.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        if self.birdsmouth:
            extension_plane_main = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        else:
            extension_plane_main = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        start_main, end_main = self.main_beam.extension_to_plane(extension_plane_main)
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

    def add_extensions(self):
        """Adds the extensions to the main beam and cross beam.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        if self.birdsmouth:
            extension_plane_main = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        else:
            extension_plane_main = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        start_main, end_main = self.main_beam.extension_to_plane(extension_plane_main)
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

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

        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        self.features = []

        if self.mill_depth:
            self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        if self.drill_diameter:
            self.cross_beam.add_features(DrillFeature(*self.calc_params_drilling()))
            self.features.append(MillVolume(self.subtraction_volume()))
        do_jack = False
        if self.birdsmouth:
            if self.calc_params_birdsmouth():
                self.main_beam.add_features(BrepSubtraction(self.bm_sub_volume))
                self.features.append(BrepSubtraction(self.bm_sub_volume))

            else:
                do_jack = True
        if do_jack:
            self.main_beam.add_features(CutFeature(cutting_plane))
            self.features.append(cutting_plane)
