from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import FrenchRidgeLap

from .lap_joint import LapJoint
from .solver import JointTopology
from .utilities import are_beams_aligned_with_cross_vector


class LFrenchRidgeLapJoint(LapJoint):
    """Represents an L-FrenchRidgeLap type joint which joins two beams at their ends, by lapping them with a ridge.
    The joint can only be created between two beams that are aligned and have the same dimensions.

    This joint type is compatible with beams in L topology.

    Please use `LFrenchRidgeLapJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, drillhole_diam=None, **kwargs):
        super(LFrenchRidgeLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, drillhole_diam, **kwargs)

        self.drillhole_diam = drillhole_diam

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam

        start_main, start_cross = None, None
        try:
            start_main, end_main = self.main_beam.extension_to_plane(self.main_cutting_plane)
            start_cross, end_cross = self.cross_beam.extension_to_plane(self.cross_cutting_plane)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cross_cutting_plane] if start_main is not None else [self.main_cutting_plane]
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_main, end_main, self.main_beam_guid)
        self.cross_beam.add_blank_extension(start_cross, end_cross, self.cross_beam_guid)

    def add_features(self):
        """Adds the necessary features to the beams.

        This method is called during the `Model.process_joinery()` process after the joint
        has been instantiated and added to the model. It is executed after the beam extensions
        have been added via `Joint.add_extensions()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        main_frl_feature = FrenchRidgeLap.from_beam_beam_and_plane(self.main_beam, self.cross_beam, self.main_cutting_plane, self.drillhole_diam, self.main_ref_side_index)
        cross_frl_feature = FrenchRidgeLap.from_beam_beam_and_plane(self.cross_beam, self.main_beam, self.cross_cutting_plane, self.drillhole_diam, self.cross_ref_side_index)
        # store the features to the beams
        self.main_beam.add_features(main_frl_feature)
        self.cross_beam.add_features(cross_frl_feature)
        # register the features in the joint
        self.features = [main_frl_feature, cross_frl_feature]

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint.

        Compared to the LapJoint's `check_elements_compatibility` method, this one additionally checks if dimensions of the beams match.

        Raises
        ------
        BeamJoiningError
            If the elements are not compatible for the creation of the joint.
        """
        if not are_beams_aligned_with_cross_vector(*self.elements):
            raise BeamJoiningError(
                beams=self.elements,
                joint=self,
                debug_info="The two beams are not coplanar to create a Lap joint.",
            )
        # calculate widths and heights of the beams
        dimensions = []
        ref_side_indices = [self.main_ref_side_index, self.cross_ref_side_index]
        for i, beam in enumerate(self.elements):
            width, height = beam.get_dimensions_relative_to_side(ref_side_indices[i])
            dimensions.append((width, height))
        # check if the dimensions of both beams match
        if dimensions[0] != dimensions[1]:
            raise BeamJoiningError(self.elements, self, debug_info="The two beams must have the same dimensions to create a French Ridge Lap joint.")

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model.element_by_guid(self.beam_a_guid)
        self.beam_b = model.element_by_guid(self.beam_b_guid)
