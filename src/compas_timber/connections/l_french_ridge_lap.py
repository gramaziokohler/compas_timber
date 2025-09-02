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

    @property
    def __data__(self):
        data = super(LFrenchRidgeLapJoint, self).__data__
        data["drillhole_diam"] = self.drillhole_diam
        return data

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, drillhole_diam=None, **kwargs):  # TODO this joint does not have main, cross beam roles
        super(LFrenchRidgeLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, **kwargs)
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

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks if the cluster of beams complies with the requirements for the LFrenchRidgeLapJoint.

        Parameters
        ----------
        elements : list(:class:`~compas_model.elements.Beam`)
            The elements to be checked.
        raise_error : bool, optional
            If True, raises a :class:`~compas_timber.errors.BeamJoiningError` if the cluster does not comply with the requirements.
            If False, returns False instead.

        Returns
        -------
        bool
            True if the cluster complies with the requirements, False otherwise.

        """
        main_beam, cross_beam = elements
        if not are_beams_aligned_with_cross_vector(main_beam, cross_beam):
            if not raise_error:
                return False

            raise BeamJoiningError(
                beams=elements,
                joint=cls,
                debug_info="The two beams are not coplanar to create a French Ridge Lap joint.",
                debug_geometries=[e.shape for e in elements],
            )

        # calculate widths and heights of the beams
        main_ref_side_index = cls._get_beam_ref_side_index(main_beam, cross_beam, flip=False)
        cross_ref_side_index = cls._get_beam_ref_side_index(cross_beam, main_beam, flip=False)

        w_main, h_main = main_beam.get_dimensions_relative_to_side(main_ref_side_index)
        w_cross, h_cross = cross_beam.get_dimensions_relative_to_side(cross_ref_side_index)

        # check if the dimensions of both beams match
        if (w_main, h_main) != (w_cross, h_cross):
            if not raise_error:
                return False

            raise BeamJoiningError(
                elements,
                cls,
                debug_info="The two beams must have the same dimensions to create a French Ridge Lap joint.",
                debug_geometries=[e.shape for e in elements],
            )

        return True
