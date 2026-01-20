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
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
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
        del data["cut_plane_bias"]
        return data

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, drillhole_diam=None, **kwargs):
        super(LFrenchRidgeLapJoint, self).__init__(beam_a, beam_b, flip_lap_side, **kwargs)
        self.drillhole_diam = drillhole_diam

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b

        start_a, start_b = None, None
        try:
            start_a, end_a = self.beam_a.extension_to_plane(self.cutting_plane_a)
            start_b, end_b = self.beam_b.extension_to_plane(self.cutting_plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cutting_plane_b] if start_a is not None else [self.cutting_plane_a]
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.beam_a.add_blank_extension(start_a, end_a, self.beam_a_guid)
        self.beam_b.add_blank_extension(start_b, end_b, self.beam_b_guid)

    def add_features(self):
        """Adds the necessary features to the beams.

        This method is called during the `Model.process_joinery()` process after the joint
        has been instantiated and added to the model. It is executed after the beam extensions
        have been added via `Joint.add_extensions()`.

        """
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        frl_feature_a = FrenchRidgeLap.from_beam_beam_and_plane(self.beam_a, self.beam_b, self.cutting_plane_a, self.drillhole_diam, self.ref_side_index_a)
        frl_feature_b = FrenchRidgeLap.from_beam_beam_and_plane(self.beam_b, self.beam_a, self.cutting_plane_b, self.drillhole_diam, self.ref_side_index_b)
        # store the features to the beams
        self.beam_a.add_features(frl_feature_a)
        self.beam_b.add_features(frl_feature_b)
        # register the features in the joint
        self.features = [frl_feature_a, frl_feature_b]

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
        beam_a, beam_b = elements
        if not are_beams_aligned_with_cross_vector(beam_a, beam_b):
            if not raise_error:
                return False

            raise BeamJoiningError(
                beams=elements,
                joint=cls,
                debug_info="The two beams are not coplanar to create a French Ridge Lap joint.",
                debug_geometries=[e.shape for e in elements],
            )

        # calculate widths and heights of the beams
        ref_side_index_a = cls._get_beam_ref_side_index(beam_a, beam_b, flip=False)
        ref_side_index_b = cls._get_beam_ref_side_index(beam_b, beam_a, flip=False)

        w_a, h_a = beam_a.get_dimensions_relative_to_side(ref_side_index_a)
        w_b, h_b = beam_b.get_dimensions_relative_to_side(ref_side_index_b)

        # check if the dimensions of both beams match
        if (w_a, h_a) != (w_b, h_b):
            if not raise_error:
                return False

            raise BeamJoiningError(
                elements,
                cls,
                debug_info="The two beams must have the same dimensions to create a French Ridge Lap joint.",
                debug_geometries=[e.shape for e in elements],
            )

        return True
