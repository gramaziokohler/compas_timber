from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Vector
from compas.geometry import intersection_line_line

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import PocketProxy

from .lap_joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence_with_vector


class XNotchJoint(Joint):
    """Represents an X-Notch type joint which joins the two beams somewhere along their length with a notch applied on the main_beam.
    This joint type is typically used to connect two beams whose centerlines are offseted from each other, resulting in one resting on top of the other through a notch.

    This joint type is compatible with beams in X topology.

    Please use `XNotchJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined. This beam will have a notch applied to it.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined. No features are applied to this beam.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined. This beam will have a notch applied to it.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined. No features are applied to this beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, beam_a=None, beam_b=None, **kwargs):
        super(XNotchJoint, self).__init__(elements=(beam_a, beam_b), **kwargs)
        self.features = []
        self._main_ref_side_index = None

    @property
    def beam_a(self):
        return self.element_a

    @property
    def beam_b(self):
        return self.element_b

    @property
    def main_ref_side_index(self):
        """The reference side index of the main beam."""
        if self._main_ref_side_index is None:
            self._main_ref_side_index = self._get_beam_ref_side_index()
        return self._main_ref_side_index

    def _get_beam_ref_side_index(self):
        """Determines the reference side index of the main beam based on the intersection of the centerlines of the two beams."""
        # get the offset vector of the two centerlines, if any
        main_beam, cross_beam = self.elements
        offset_vector = Vector.from_start_end(*intersection_line_line(main_beam.centerline, cross_beam.centerline))
        cross_vector = main_beam.centerline.direction.cross(cross_beam.centerline.direction)
        # flip the cross_vector if it is pointing in the opposite direction of the offset_vector
        if cross_vector.dot(offset_vector) < 0:
            cross_vector = -cross_vector
        ref_side_dict = beam_ref_side_incidence_with_vector(main_beam, cross_vector, ignore_ends=True)
        return min(ref_side_dict, key=ref_side_dict.get)

    def _create_negative_volume(self):
        """Creates a negative volume for the X-Notch joint.

        This method creates a negative volume that represents the notch to be applied to the main beam.
        It uses the blank of the cross beam and trims it with the side frames of the main beam.
        The negative volume is then used to create a pocket feature on the main beam.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The negative volume representing the notch.
        """
        assert self.elements
        main_beam, cross_beam = self.elements

        # create a Brep from the cross beam's blank
        neg_vol = Brep.from_box(cross_beam.blank)
        side_cutting_frames = [main_beam.front_side(self.main_ref_side_index), main_beam.back_side(self.main_ref_side_index)]
        # trim the negative volume with the side frames of the main beam
        for frame in side_cutting_frames:
            try:
                neg_vol.trim(frame)
            except BrepTrimmingError as bte:
                raise BeamJoiningError(
                    beams=self.elements,
                    joint=self,
                    debug_info="Failed to generate the negative volume used to create the notch feature: {}".format(str(bte)),
                )
        return neg_vol

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # create pocket features
        negative_volume = self._create_negative_volume()
        pocket_feature = PocketProxy.from_volume_and_element(negative_volume, self.main_beam, ref_side_index=self.main_ref_side_index)

        # add features to the beams
        self.main_beam.add_features(pocket_feature)

        # register processings to the joint
        self.features.append(pocket_feature)
