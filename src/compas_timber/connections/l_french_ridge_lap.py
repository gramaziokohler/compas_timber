from compas.tolerance import TOL

from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.errors import BeamJoinningError
from compas_timber.fabrication import FrenchRidgeLap

from .joint import Joint
from .solver import JointTopology


class LFrenchRidgeLapJoint(Joint):
    """Represents an L-FrenchRidgeLap type joint which joins two beams in their ends, by lapping them with a ridge.
    The joint can only be created between two beams that are aligned and have the same dimensions.

    This joint type is compatible with beams in L topology.

    Please use `LFrenchRidgeLapJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.
    flip_beams : bool
        If True, the beams will be flipped in the joint. Default is False.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    drillhole_diam : float
        Diameter of the drill hole to be made in the joint.
    flip_beams : bool
        If True, the beams will be flipped in the joint. Default is False.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LFrenchRidgeLapJoint, self).__data__
        data["beam_a_guid"] = self.beam_a_guid
        data["beam_b_guid"] = self.beam_b_guid
        data["drillhole_diam"] = self.drillhole_diam
        data["flip_beams"] = self.flip_beams
        return data

    def __init__(self, beam_a=None, beam_b=None, drillhole_diam=None, flip_beams=None, **kwargs):
        super(LFrenchRidgeLapJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = kwargs.get("beam_a_guid", None) or str(beam_a.guid)
        self.beam_b_guid = kwargs.get("beam_b_guid", None) or str(beam_b.guid)

        self.drillhole_diam = drillhole_diam
        self.flip_beams = flip_beams
        self.features = []

    @property
    def elements(self):
        return [self.beam_a, self.beam_b]

    @property
    def beam_a_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_a, cross_vector, ignore_ends=True)
        if self.flip_beams:
            return max(ref_side_dict, key=ref_side_dict.get)
        return min(ref_side_dict, key=ref_side_dict.get)

    @property
    def beam_b_ref_side_index(self):
        cross_vector = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.beam_b, cross_vector, ignore_ends=True)
        if self.flip_beams:
            return min(ref_side_dict, key=ref_side_dict.get)
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

        This method is called during the `Model.process_joinery()` process after the joint
        has been instantiated and added to the model.

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
            raise BeamJoinningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.elements, self, debug_info=str(ex))
        self.beam_a.add_blank_extension(start_a, end_a, self.guid)
        self.beam_b.add_blank_extension(start_b, end_b, self.guid)

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

        frl_a = FrenchRidgeLap.from_beam_beam_and_plane(
            self.beam_a, self.beam_b, self.cutting_plane_b, self.drillhole_diam, self.beam_a_ref_side_index
        )
        frl_b = FrenchRidgeLap.from_beam_beam_and_plane(
            self.beam_b, self.beam_a, self.cutting_plane_a, self.drillhole_diam, self.beam_b_ref_side_index
        )
        self.beam_a.add_features(frl_a)
        self.beam_b.add_features(frl_b)
        self.features = [frl_a, frl_b]

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint.

        Raises
        ------
        BeamJoinningError
            If the elements are not compatible for the creation of the joint.

        """
        # check if the beams are aligned
        cross_vect = self.beam_a.centerline.direction.cross(self.beam_b.centerline.direction)
        for beam in self.elements:
            beam_normal = beam.frame.normal.unitized()
            dot = abs(beam_normal.dot(cross_vect.unitized()))
            if not (TOL.is_zero(dot) or TOL.is_close(dot, 1)):
                raise BeamJoinningError(
                    self.beam_a,
                    self.beam_b,
                    debug_info="The the two beams are not aligned to create a French Ridge Lap joint.",
                )
        # calculate widths and heights of the beams
        dimensions = []
        ref_side_indices = [self.beam_a_ref_side_index, self.beam_b_ref_side_index]
        for i, beam in enumerate(self.elements):
            width = beam.side_as_surface(ref_side_indices[i]).ysize
            height = beam.height if ref_side_indices[i] % 2 == 0 else beam.width
            dimensions.append((width, height))
        # check if the dimensions of both beams match
        if dimensions[0] != dimensions[1]:
            raise BeamJoinningError(self.beam_a, self.beam_b, debug_info="The beams have different dimensions.")

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model.element_by_guid(self.beam_a_guid)
        self.beam_b = model.element_by_guid(self.beam_b_guid)
