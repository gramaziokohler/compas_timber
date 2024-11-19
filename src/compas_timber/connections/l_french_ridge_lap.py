from compas_timber._fabrication import FrenchRidgeLap
from compas_timber._fabrication.btlx_process import EdgePositionType
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class LFrenchRidgeLapJoint(Joint):
    """Represents an L-FrenchRidgeLap type joint which joins two beams in their ends, by lapping them with a ridge.

    This joint type is compatible with beams in L topology.

    Please use `LFrenchRidgeLapJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LFrenchRidgeLapJoint, self).__data__
        data["beam_a"] = self.beam_a_guid
        data["beam_b"] = self.beam_b_guid
        data["drillhole_diam"] = self.drillhole_diam
        return data

    def __init__(self, beam_a=None, beam_b=None, drillhole_diam=None, **kwargs):
        super(LFrenchRidgeLapJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = kwargs.get("beam_a_guid", None) or str(beam_a.guid)
        self.beam_b_guid = kwargs.get("beam_b_guid", None) or str(beam_b.guid)

        self.drillhole_diam = drillhole_diam
        self.features = []

    @property
    def beams(self):
        return [self.beam_a, self.beam_b]

    @property
    def beam_a_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_a, cross_vector, ignore_ends=True)
        return min(ref_side_dict, key=ref_side_dict.get)

    @property
    def beam_b_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_b, cross_vector, ignore_ends=True)
        return max(ref_side_dict, key=ref_side_dict.get)

    @property
    def cutting_plane_a(self):
        # the plane that cuts beam_b
        ref_side_dict = beam_ref_side_incidence(self.beam_b, self.beam_a, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.beam_a.ref_sides[ref_side_index]

    @property
    def cutting_plane_b(self):
        # the plane that cuts beam_a
        ref_side_dict = beam_ref_side_incidence(self.beam_a, self.beam_b, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return self.beam_b.ref_sides[ref_side_index]

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
        try:
            start_a, end_a = self.beam_a.extension_to_plane(self.cutting_plane_b)
            start_b, end_b = self.beam_b.extension_to_plane(self.cutting_plane_a)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [self.cutting_plane_a] if start_a is not None else [self.cutting_plane_b]
            raise BeamJoinningError(self.beams, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.beams, self, debug_info=str(ex))
        self.beam_a.add_blank_extension(start_a, end_a, self.guid)
        self.beam_b.add_blank_extension(start_b, end_b, self.guid)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        frl_a = FrenchRidgeLap.from_plane_and_beam(
            self.cutting_plane_b, self.beam_a, self.drillhole_diam, self.beam_a_ref_side_index
        )
        frl_b = FrenchRidgeLap.from_plane_and_beam(
            self.cutting_plane_a, self.beam_b, self.drillhole_diam, self.beam_b_ref_side_index
        )
        self.beam_a.add_features(frl_a)
        self.beam_b.add_features(frl_b)
        self.features = [frl_a, frl_b]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model.element_by_guid(self.beam_a_guid)
        self.beam_b = model.element_by_guid(self.beam_b_guid)
