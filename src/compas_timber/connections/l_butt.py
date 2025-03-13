from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class LButtJoint(Joint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will reject beams in I topology.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will reject beams in I topology.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        data["small_beam_butts"] = self.small_beam_butts
        data["modify_cross"] = self.modify_cross
        data["reject_i"] = self.reject_i
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, small_beam_butts=False, modify_cross=True, reject_i=False, **kwargs):
        super(LButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth = mill_depth
        self.small_beam_butts = small_beam_butts
        self.modify_cross = modify_cross
        self.reject_i = reject_i
        self.features = []

        # update the main and cross beams based on the joint parameters
        self.update_beam_roles()

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

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
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info="Beams are in I topology and reject_i flag is True")
        return ref_side_index

    def update_beam_roles(self):
        """Flips the main and cross beams based on the joint parameters.
        Prioritizes the beam with the smaller cross-section if `small_beam_butts` is True.

        """
        if self.small_beam_butts:
            if self.main_beam.width * self.main_beam.height > self.cross_beam.width * self.cross_beam.height:
                self.main_beam, self.cross_beam = self.cross_beam, self.main_beam

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam

        # extend the main beam
        if self.mill_depth:
            try:
                cutting_plane_main = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
                if self.mill_depth:
                    cutting_plane_main.translate(-cutting_plane_main.normal * self.mill_depth)
                start_main, end_main = self.main_beam.extension_to_plane(cutting_plane_main)
            except AttributeError as ae:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane_main])
            except Exception as ex:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.main_beam.add_blank_extension(
                start_main + extension_tolerance,
                end_main + extension_tolerance,
                self.guid,
            )
        # extend the cross beam
        try:
            cutting_plane_cross = self.main_beam.opp_side(self.main_beam_ref_side_index)
            start_cross, end_cross = self.cross_beam.extension_to_plane(cutting_plane_cross)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane_cross])
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.cross_beam.add_blank_extension(
            start_cross + extension_tolerance,
            end_cross + extension_tolerance,
            self.guid,
        )

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # get the cutting plane for the main beam
        cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        cutting_plane.xaxis = -cutting_plane.xaxis
        if self.mill_depth:
            cutting_plane.translate(cutting_plane.normal * self.mill_depth)

        # apply the cut on the main beam
        main_feature = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.main_beam, self.main_beam_ref_side_index)
        self.main_beam.add_features(main_feature)
        # store the feature
        self.features = [main_feature]

        # apply the pocket on the cross beam
        if self.mill_depth:
            cross_cutting_plane = self.main_beam.ref_sides[self.main_beam_ref_side_index]
            lap_width = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[1]
            cross_feature = Lap.from_plane_and_beam(
                cross_cutting_plane,
                self.cross_beam,
                lap_width,
                self.mill_depth,
                ref_side_index=self.cross_beam_ref_side_index,
            )
            self.cross_beam.add_features(cross_feature)
            self.features.append(cross_feature)

        # apply a refinement cut on the cross beam
        if self.modify_cross:
            modification_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
            cross_refinement_feature = JackRafterCutProxy.from_plane_and_beam(modification_plane, self.cross_beam, self.cross_beam_ref_side_index)
            self.cross_beam.add_features(cross_refinement_feature)
            self.features.append(cross_refinement_feature)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
