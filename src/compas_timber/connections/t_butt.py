from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class TButtJoint(Joint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, fastener=None, **kwargs):
        super(TButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth = mill_depth
        self.features = []
        self.fasteners = []
        if fastener:
            if fastener.outline is None:
                fastener = fastener.copy()  # make a copy to avoid modifying the original fastener
                fastener.set_default(joint=self)
            self.base_fastener = fastener
            if self.base_fastener:
                self.base_fastener.place_instances(self)

    @property
    def interactions(self):
        """Returns interactions between elements used by this joint."""
        interactions = []
        interactions.append((self.main_beam, self.cross_beam))
        for fastener in self.fasteners:
            for interface in fastener.interfaces:
                if interface is not None:
                    interactions.append((interface.element, fastener))
        return interactions

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def elements(self):
        return self.beams + self.fasteners

    @property
    def generated_elements(self):
        return self.fasteners

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        try:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            if self.mill_depth:
                cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
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
            lap_length = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[1]

            cross_feature = Lap.from_plane_and_beam(
                cross_cutting_plane,
                self.cross_beam,
                lap_length,
                self.mill_depth,
                ref_side_index=self.cross_beam_ref_side_index,
            )
            self.cross_beam.add_features(cross_feature)
            self.features.append(cross_feature)

        # add the features applied by the fastener.interfaces
        for fastener in self.fasteners:
            for interface in fastener.interfaces:
                features = interface.get_features(interface.element)
                interface.element.add_features(features)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
