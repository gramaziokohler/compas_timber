from compas_timber._fabrication import JackRafterCut
from compas_timber._fabrication import Lap
from compas_timber.connections.utilities import beam_ref_side_incidence

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class LButtJoint(Joint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.



    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        **kwargs
    ):
        super(Joint, self).__init__(**kwargs)
        self.elements = [main_beam, cross_beam]


        # update the main and cross beams based on the joint parameters
        self.update_beam_roles()

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]
    
    @property
    def main_beam(self):
        return self.elements[0]
    
    @property
    def cross_beam(self):
        return self.elements[1]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

        if self.reject_i and ref_side_index in [4, 5]:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info="Beams are in I topology and reject_i flag is True"
            )
        return ref_side_index

    @property
    def main_beam_opposing_side_index(self):
        return self.main_beam.opposing_side_index(self.main_beam_ref_side_index)

    def update_beam_roles(self):
        """Flips the main and cross beams based on the joint parameters.
        Prioritizes the beam with the smaller cross-section if `small_beam_butts` is True.

        """
        if self.small_beam_butts:
            if self.main_beam.width * self.main_beam.height > self.cross_beam.width * self.cross_beam.height:
                self.main_beam, self.cross_beam = self.cross_beam, self.main_beam

    def extend_main_beam(self):
        """Calculates and adds the necessary extensions to the main beam.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam

        # extend the main beam
        if self.mill_depth:
            try:
                cutting_plane_main = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
                cutting_plane_main.translate(-cutting_plane_main.normal * self.mill_depth)
                start_main, end_main = self.main_beam.extension_to_plane(cutting_plane_main)
            except AttributeError as ae:
                raise BeamJoinningError(
                    beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane_main]
                )
            except Exception as ex:
                raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.main_beam.add_blank_extension(
                start_main + extension_tolerance,
                end_main + extension_tolerance,
                self.guid,
            )
 

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
