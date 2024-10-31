from compas.geometry import Plane
from compas.geometry import distance_point_line
from compas.geometry import intersection_plane_plane_plane

from compas_timber._fabrication import DoubleCut
from compas_timber.connections.utilities import beam_ref_side_incidence

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class TBirdsmouthJoint(Joint):
    """Represents a T-Birdsmouth type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).

    This joint type is compatible with beams in T topology.

    Please use `TBirdsmouth.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.

    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.

    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TBirdsmouthJoint, self).__data__
        data["main_beam"] = self.main_beam_guid
        data["cross_beam"] = self.cross_beam_guid
        return data

    def __init__(self, main_beam, cross_beam):
        super(TBirdsmouthJoint, self).__init__()
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None

        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_indices(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_indices = sorted(ref_side_dict, key=ref_side_dict.get)[:2]
        return ref_side_indices

    @property
    def main_beam_ref_side_index(self):
        distance_dict = {}
        cutting_frames = [self.cross_beam.ref_sides[index] for index in self.cross_beam_ref_side_indices]
        for i, ref_side in enumerate(self.main_beam.ref_sides[0:4]):
            intercection_pt = intersection_plane_plane_plane(
                Plane.from_frame(cutting_frames[0]), Plane.from_frame(cutting_frames[1]), Plane.from_frame(ref_side)
            )
            distance_dict[i] = distance_point_line(intercection_pt, self.main_beam.centerline)
        return min(distance_dict.keys(), key=distance_dict.get)

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        start_a, end_a = None, None

        face_index = self.cross_beam_ref_side_indices[1]
        plane = self.cross_beam.ref_sides[face_index]

        try:
            start_a, end_a = self.main_beam.extension_to_plane(plane)
        except Exception as ex:
            raise BeamJoinningError(self.beams, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.guid)

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        cross_beam_ref_sides = [self.cross_beam.ref_sides[index] for index in self.cross_beam_ref_side_indices]

        # generate step joint features
        main_feature = DoubleCut.from_planes_and_beam(
            cross_beam_ref_sides, self.main_beam, self.main_beam_ref_side_index
        )

        # add features to beams
        self.main_beam.add_features(main_feature)
        # add features to joint
        self.features = main_feature

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.elementdict[self.main_beam_guid]
        self.cross_beam = model.elementdict[self.cross_beam_guid]
