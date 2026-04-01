import math

from compas.geometry import Plane
from compas.geometry import angle_vectors
from compas.geometry import distance_point_line
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap

from .lap_joint import LapJoint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence_with_vector


class ILapJoint(LapJoint):
    """Represents an I-Lap type joint which joins continuously two beams with a lap.

    This joint type is compatible with beams in I topology.

    Please use `ILapJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_I

    @property
    def ref_side_index_a(self):
        """The reference side index of beam_a for parallel I-topology beams."""
        if self._ref_side_index_a is None:
            vector = -self.beam_a.frame.normal if self.flip_lap_side else self.beam_a.frame.normal
            ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_a, vector, ignore_ends=True)
            self._ref_side_index_a = min(ref_side_dict, key=ref_side_dict.get)
        return self._ref_side_index_a

    @property
    def ref_side_index_b(self):
        """The reference side index of beam_b opposite to beam_a for a scarf-like overlap."""
        if self._ref_side_index_b is None:
            vector = self.beam_a.frame.normal if self.flip_lap_side else -self.beam_a.frame.normal
            ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_b, vector, ignore_ends=True)
            self._ref_side_index_b = min(ref_side_dict, key=ref_side_dict.get)
        return self._ref_side_index_b

    @staticmethod
    def _lap_length(beam_a, beam_b):
        return min(beam_a.height, beam_b.height)

    def _joint_end_sides(self):
        return self._select_joint_end_sides(self.beam_a, self.beam_b, require_opposite_outward=True)

    def _joint_end_indices(self):
        side_a, side_b = self._joint_end_sides()
        return self._end_index_from_side(side_a), self._end_index_from_side(side_b)

    def _joint_end_state(self):
        side_a, side_b = self._joint_end_sides()
        point_a = self._endpoint_point(self.beam_a, side_a)
        point_b = self._endpoint_point(self.beam_b, side_b)
        outward_a = self._outward_vector(self.beam_a, side_a)
        signed_separation = (point_b - point_a).dot(outward_a)
        return side_a, side_b, point_a, point_b, signed_separation

    def _assert_is_continuous_i_topology(self):
        angle = angle_vectors(self.beam_a.centerline.direction, self.beam_b.centerline.direction)
        is_parallel = TOL.is_zero(angle) or TOL.is_zero(angle - math.pi)
        if not is_parallel:
            raise BeamJoiningError("ILapJoint only supports continuous beams in I topology.")

        is_colinear = TOL.is_zero(distance_point_line(self.beam_a.centerline.start, self.beam_b.centerline)) and TOL.is_zero(
            distance_point_line(self.beam_a.centerline.end, self.beam_b.centerline)
        )
        if not is_colinear:
            raise BeamJoiningError("ILapJoint only supports continuous beams in I topology.")

    def _cutting_setup(self):
        side_a, side_b, point_a, point_b, signed_separation = self._joint_end_state()
        end_index_a = self._end_index_from_side(side_a)
        end_index_b = self._end_index_from_side(side_b)

        base_plane_a = Plane.from_frame(self.beam_a.ref_sides[end_index_a])
        base_plane_b = Plane.from_frame(self.beam_b.ref_sides[end_index_b])

        overlap_length = max(0.0, -signed_separation)
        lap_length = self._lap_length(self.beam_a, self.beam_b)
        trim_each = max(0.0, (overlap_length - lap_length) * 0.5)

        if trim_each > TOL.absolute:
            shift_a = -self.beam_a.centerline.direction * trim_each if side_a == "end" else self.beam_a.centerline.direction * trim_each
            shift_b = -self.beam_b.centerline.direction * trim_each if side_b == "end" else self.beam_b.centerline.direction * trim_each
            plane_a = Plane(base_plane_a.point + shift_a, base_plane_a.normal)
            plane_b = Plane(base_plane_b.point + shift_b, base_plane_b.normal)
        else:
            plane_a = base_plane_a
            plane_b = base_plane_b

        return {
            "side_a": side_a,
            "side_b": side_b,
            "point_a": point_a,
            "point_b": point_b,
            "signed_separation": signed_separation,
            "lap_length": lap_length,
            "trim_each": trim_each,
            "plane_a": plane_a,
            "plane_b": plane_b,
        }

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b
        self._assert_is_continuous_i_topology()

        setup = self._cutting_setup()
        side_a = setup["side_a"]
        side_b = setup["side_b"]
        point_a = setup["point_a"]
        point_b = setup["point_b"]
        signed_separation = setup["signed_separation"]
        lap_length = setup["lap_length"]

        total_required_extension = max(0.0, lap_length + signed_separation)
        extension_each = 0.5 * total_required_extension + TOL.absolute

        start_a = extension_each if side_a == "start" else 0.0
        end_a = extension_each if side_a == "end" else 0.0
        start_b = extension_each if side_b == "start" else 0.0
        end_b = extension_each if side_b == "end" else 0.0

        try:
            self.beam_a.add_blank_extension(start_a, end_a, self.guid)
            self.beam_b.add_blank_extension(start_b, end_b, self.guid)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex), debug_geometries=[point_a, point_b])

    def add_features(self):
        """Adds the required joint features to both beams."""
        assert self.beam_a and self.beam_b
        self._assert_is_continuous_i_topology()

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        setup = self._cutting_setup()
        lap_length = setup["lap_length"]
        trim_each = setup["trim_each"]
        cutting_plane_a = setup["plane_a"]
        cutting_plane_b = setup["plane_b"]

        depth_a = self.beam_a.height * self.cut_plane_bias
        depth_b = self.beam_b.height * (1.0 - self.cut_plane_bias)

        try:
            lap_feature_a = Lap.from_plane_and_beam(cutting_plane_a, self.beam_a, lap_length, depth_a, ref_side_index=self.ref_side_index_a)
            lap_feature_b = Lap.from_plane_and_beam(cutting_plane_b, self.beam_b, lap_length, depth_b, ref_side_index=self.ref_side_index_b)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex), debug_geometries=[cutting_plane_a, cutting_plane_b])

        features_a = [lap_feature_a]
        features_b = [lap_feature_b]

        if trim_each > TOL.absolute:
            trim_feature_a = JackRafterCutProxy.from_plane_and_beam(cutting_plane_a, self.beam_a)
            trim_feature_b = JackRafterCutProxy.from_plane_and_beam(cutting_plane_b, self.beam_b)
            features_a.insert(0, trim_feature_a)
            features_b.insert(0, trim_feature_b)

        # add processings to beams
        self.beam_a.add_features(features_a)
        self.beam_b.add_features(features_b)

        # register processings to the joint
        self.features.extend(features_a + features_b)
