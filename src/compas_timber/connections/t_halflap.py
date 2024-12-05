from compas_timber._fabrication import JackRafterCut
from compas_timber._fabrication import Lap
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.connections.utilities import beam_ref_side_incidence

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology

from compas.tolerance import TOL


class THalfLapJoint(Joint):
    """Represents a T-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `THalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

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
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(THalfLapJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=None, cut_plane_bias=None, **kwargs):
        super(THalfLapJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = 0.5 if cut_plane_bias is None else cut_plane_bias
        self.features = []

        # check if the geometry is valid. (beams should be aligned)
        self._check_geometry()  # TODO: in the future, half laps should be possible for non-aligned beams

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_ref_side_index(self):
        cross_vector = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return max(ref_side_dict, key=ref_side_dict.get)
        return min(ref_side_dict, key=ref_side_dict.get)

    @property
    def main_ref_side_index(self):
        cross_vector = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return min(ref_side_dict, key=ref_side_dict.get)
        return max(ref_side_dict, key=ref_side_dict.get)

    @property
    def cross_cutting_plane(self):
        # the plane that cuts cross_beam as a planar surface
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.main_beam.side_as_surface(ref_side_index)

    @property
    def main_cutting_plane(self):
        # the plane that cuts main_beam as a planar surface
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.cross_beam.side_as_surface(ref_side_index)

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
            start_main, end_main = self.main_beam.extension_to_plane(self.main_cutting_plane.to_plane())
        except AttributeError as ae:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[self.main_cutting_plane.to_plane()]
            )
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
            self.guid,
        )

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # calculate the lap length and depth for each beam
        cross_lap_length, main_lap_length = self._get_lap_lengths()
        cross_lap_depth, main_lap_depth = self._get_lap_depths()

        ## cross_beam features
        # cross Lap feature
        cross_lap_feature = Lap.from_plane_and_beam(
            self.cross_cutting_plane.to_plane(),
            self.cross_beam,
            cross_lap_length,
            cross_lap_depth,
            ref_side_index=self.cross_ref_side_index,
        )
        # register features to the joint
        self.cross_beam.add_features(cross_lap_feature)
        self.features.append(cross_lap_feature)

        ## main_beam features
        # main Lap feature
        main_lap_feature = Lap.from_plane_and_beam(
            self.main_cutting_plane.to_plane(),
            self.main_beam,
            main_lap_length,
            main_lap_depth,
            ref_side_index=self.main_ref_side_index,
        )
        # cutoff feature for main beam
        main_cutoff_feature = JackRafterCut.from_plane_and_beam(
            self.main_cutting_plane.to_plane(), self.main_beam, self.main_ref_side_index
        )
        # register features to the joint
        main_features = [main_lap_feature, main_cutoff_feature]
        self.main_beam.add_features(main_features)
        self.features.extend(main_features)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)

    def _check_geometry(self):
        """Checks if the geometry of the beams is valid for the joint.

        Raises
        ------
        BeamJoinningError
            If the geometry is invalid.

        """
        # check if the beams are aligned
        for beam in self.beams:
            cross_vector = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
            beam_normal = beam.frame.normal.unitized()
            dot = abs(beam_normal.dot(cross_vector.unitized()))
            if not (TOL.is_zero(dot) or TOL.is_close(dot, 1)):
                raise BeamJoinningError(
                    self.beams,
                    self,
                    debug_info="The two beams are not aligned to create a Half Lap joint.",
                )

    def _get_lap_lengths(self):
        cross_lap_length = self.main_beam.side_as_surface(self.main_ref_side_index).ysize
        main_lap_length = self.cross_beam.side_as_surface(self.cross_ref_side_index).ysize
        return cross_lap_length, main_lap_length

    def _get_lap_depths(self):
        lap_depth = (self.main_cutting_plane.ysize + self.cross_cutting_plane.ysize) / 2
        return lap_depth * self.cut_plane_bias, lap_depth * (1 - self.cut_plane_bias)
