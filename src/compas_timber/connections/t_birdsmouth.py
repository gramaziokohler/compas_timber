from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import Lap

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class TBirdsmouthJoint(Joint):
    """Represents a T-Birdsmouth type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).

    This joint type is compatible with beams in T topology.

    Please use `TBirdsmouth.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    mill_depth : float
        The depth of the pockets to be milled on the cross beam.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    mill_depth : float
        The depth of the pockets to be milled on the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TBirdsmouthJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, **kwargs):
        super(TBirdsmouthJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth = mill_depth

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_ref_side_indices(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_indices = sorted(ref_side_dict, key=ref_side_dict.get)[:2]
        return ref_side_indices

    def _get_cutting_planes(self):
        cutting_planes = [self.cross_beam.ref_sides[index] for index in self.cross_ref_side_indices]
        if self.mill_depth:
            cutting_planes = [plane.translated(-plane.normal * self.mill_depth) for plane in cutting_planes]
        return cutting_planes

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        start_a, end_a = None, None

        face_index = self.cross_ref_side_indices[1]
        plane = self.cross_beam.ref_sides[face_index]

        if self.mill_depth:
            plane.translate(-plane.normal * self.mill_depth)

        try:
            start_a, end_a = self.main_beam.extension_to_plane(plane)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.guid)

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        cutting_planes = self._get_cutting_planes()

        # generate double cut feature
        main_feature = DoubleCut.from_planes_and_beam(cutting_planes, self.main_beam)

        # register main feature to beam and joint
        self.main_beam.add_features(main_feature)
        self.features.append(main_feature)

        if self.mill_depth:
            main_ref_side_index = main_feature.ref_side_index
            lap_cutting_plane = self.main_beam.ref_sides[main_ref_side_index]
            lap_length = self.main_beam.get_dimensions_relative_to_side(main_ref_side_index)[1]

            # generate lap feature for each side of the cross beam that intersects the main beam
            # TODO: replace with Pocket once implemented in order to get a better fit
            cross_feature_1 = Lap.from_plane_and_beam(
                lap_cutting_plane,
                self.cross_beam,
                lap_length,
                self.mill_depth,
                is_pocket=True,
                ref_side_index=self.cross_ref_side_indices[0],
            )
            cross_feature_2 = Lap.from_plane_and_beam(
                lap_cutting_plane,
                self.cross_beam,
                lap_length,
                self.mill_depth,
                is_pocket=True,
                ref_side_index=self.cross_ref_side_indices[1],
            )

            # register cross features to beam and joint
            self.cross_beam.add_features([cross_feature_1, cross_feature_2])
            self.features.extend([cross_feature_1, cross_feature_2])

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
