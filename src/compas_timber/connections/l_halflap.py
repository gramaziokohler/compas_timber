from compas.tolerance import TOL

from compas_timber._fabrication import JackRafterCut
from compas_timber._fabrication import Lap
from compas_timber.errors import BeamJoinningError

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class LHalfLapJoint(Joint):
    """Represents a L-Lap type joint which joins the ends of two beams,
    trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LHalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LHalfLapJoint, self).__data__
        data["beam_a"] = self.beam_a_guid
        data["beam_b"] = self.beam_b_guid
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=None, cut_plane_bias=None, **kwargs):
        super(LHalfLapJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = kwargs.get("beam_a_guid", None) or str(beam_a.guid)
        self.beam_b_guid = kwargs.get("beam_b_guid", None) or str(beam_b.guid)

        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = 0.5 if cut_plane_bias is None else cut_plane_bias
        self.features = []

    @property
    def elements(self):
        return [self.beam_a, self.beam_b]

    @property
    def beam_a_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_a, cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return max(ref_side_dict, key=ref_side_dict.get)
        return min(ref_side_dict, key=ref_side_dict.get)

    @property
    def beam_b_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_b, cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return min(ref_side_dict, key=ref_side_dict.get)
        return max(ref_side_dict, key=ref_side_dict.get)

    @property
    def cutting_plane_a(self):
        # the plane that cuts beam_a as a planar surface
        ref_side_dict = beam_ref_side_incidence(self.beam_a, self.beam_b, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.beam_b.side_as_surface(ref_side_index)

    @property
    def cutting_plane_b(self):
        # the plane that cuts beam_b as a planar surface
        ref_side_dict = beam_ref_side_incidence(self.beam_b, self.beam_a, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.beam_a.side_as_surface(ref_side_index)

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b
        start_a, start_b = None, None
        cutting_plane_a = self.cutting_plane_a.to_plane()
        cutting_plane_b = self.cutting_plane_b.to_plane()
        try:
            start_a, end_a = self.beam_a.extension_to_plane(cutting_plane_a)
            start_b, end_b = self.beam_b.extension_to_plane(cutting_plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [cutting_plane_b] if start_a is not None else [cutting_plane_a]
            raise BeamJoinningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.elements, self, debug_info=str(ex))
        self.beam_a.add_blank_extension(start_a, end_a, self.beam_a_guid)
        self.beam_b.add_blank_extension(start_b, end_b, self.beam_b_guid)

    def add_features(self):
        """Adds the required joint features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        # calculate the lap length and depth for each beam
        beam_a_lap_length, beam_b_lap_length = self._get_lap_lengths()
        beam_a_lap_depth, beam_b_lap_depth = self._get_lap_depths()

        ## beam_a
        # lap feature on beam_a
        lap_feature_a = Lap.from_plane_and_beam(
            self.cutting_plane_a.to_plane(),
            self.beam_a,
            beam_a_lap_length,
            beam_a_lap_depth,
            ref_side_index=self.beam_a_ref_side_index,
        )
        # cutoff feature for beam_a
        cutoff_feature_a = JackRafterCut.from_plane_and_beam(
            self.cutting_plane_a.to_plane(), self.beam_a, self.beam_a_ref_side_index
        )
        beam_a_features = [lap_feature_a, cutoff_feature_a]
        self.beam_a.add_features(beam_a_features)
        self.features.extend(beam_a_features)

        ## beam_b
        # lap feature on beam_b
        lap_feature_b = Lap.from_plane_and_beam(
            self.cutting_plane_b.to_plane(),
            self.beam_b,
            beam_b_lap_length,
            beam_b_lap_depth,
            ref_side_index=self.beam_b_ref_side_index,
        )
        # cutoff feature for beam_b
        cutoff_feature_b = JackRafterCut.from_plane_and_beam(
            self.cutting_plane_b.to_plane(), self.beam_b, self.beam_b_ref_side_index
        )
        beam_b_features = [lap_feature_b, cutoff_feature_b]
        self.beam_b.add_features(beam_b_features)
        self.features.extend(beam_b_features)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model.element_by_guid(self.beam_a_guid)
        self.beam_b = model.element_by_guid(self.beam_b_guid)

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint.

        Raises
        ------
        BeamJoinningError
            If the elements are not compatible for the creation of the joint.
        """
        # check if the beams are aligned
        for beam in self.elements:
            cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
            beam_normal = beam.frame.normal.unitized()
            dot = abs(beam_normal.dot(cross_vector.unitized()))
            if not (TOL.is_zero(dot) or TOL.is_close(dot, 1)):
                raise BeamJoinningError(
                    self.elements,
                    self,
                    debug_info="The the two beams are not aligned to create a Half Lap joint.",
                )

    def _get_lap_lengths(self):
        lap_a_length = self.beam_b.side_as_surface(self.beam_b_ref_side_index).ysize
        lap_b_length = self.beam_a.side_as_surface(self.beam_a_ref_side_index).ysize
        return lap_a_length, lap_b_length

    def _get_lap_depths(self):
        lap_depth = (self.cutting_plane_a.ysize + self.cutting_plane_b.ysize) / 2
        return lap_depth * self.cut_plane_bias, lap_depth * (1 - self.cut_plane_bias)
