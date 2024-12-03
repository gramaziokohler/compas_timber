from compas_timber._fabrication import Lap
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class XHalfLapJoint(Joint):
    """Represents a X-Lap type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `XHalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

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

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    # def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, **kwargs):
    #     super(XHalfLapJoint, self).__init__(main_beam, cross_beam, flip_lap_side, cut_plane_bias, **kwargs)

    @property
    def __data__(self):
        data = super(XHalfLapJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, **kwargs):
        super(XHalfLapJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth = mill_depth
        self.features = []

        self.cross_vector = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, self.cross_vector, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, self.cross_vector, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # apply the pocket on the cross beam
        if self.mill_depth:
            cross_cutting_plane = self.main_beam.ref_sides[(self.main_beam_ref_side_index + 1) % 4]
            lap_width = self.main_beam.height if self.main_beam_ref_side_index % 2 == 0 else self.main_beam.width
            cross_feature = Lap.from_planes_and_beam(
                cross_cutting_plane,
                self.cross_beam,
                lap_width,
                self.mill_depth,
                (self.cross_beam_ref_side_index),
            )
            self.cross_beam.add_features(cross_feature)

            main_cutting_plane = self.cross_beam.ref_sides[(self.cross_beam_ref_side_index + 1) % 4]
            lap_width_2 = self.cross_beam.height if self.cross_beam_ref_side_index % 2 == 0 else self.cross_beam.width
            main_feature = Lap.from_planes_and_beam(
                main_cutting_plane,
                self.main_beam,
                lap_width_2,
                self.mill_depth,
                (self.main_beam_ref_side_index),
            )
            self.main_beam.add_features(main_feature)

            self.features = [cross_feature, main_feature]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
