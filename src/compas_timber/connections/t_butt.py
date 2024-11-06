from compas_timber._fabrication import JackRafterCut
from compas_timber._fabrication import Lap
from compas_timber.connections.utilities import beam_ref_side_incidence

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class TButtJoint(Joint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with an model.

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
        data["main_beam"] = self.main_beam_guid
        data["cross_beam"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None):
        super(TButtJoint, self).__init__()
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        try:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
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
        cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index-1]
        cutting_plane.xaxis = -cutting_plane.xaxis
        if self.mill_depth:
            cutting_plane.translate(cutting_plane.normal * self.mill_depth)

        # apply the cut on the main beam
        main_feature = JackRafterCut.from_plane_and_beam(
            cutting_plane, self.main_beam, (self.main_beam_ref_side_index) % 4
        )
        self.main_beam.add_features(main_feature)

        # store the feature
        self.features = [main_feature]

        # apply the pocket on the cross beam
        if self.mill_depth:
            cross_cutting_planes = (
                self.main_beam.ref_sides[self.main_beam_ref_side_index],
                self.main_beam.ref_sides[(self.main_beam_ref_side_index + 2) % 4],
            )
            cross_feature = Lap.from_two_planes_and_beam(
                cross_cutting_planes, self.cross_beam, self.mill_depth, self.cross_beam_ref_side_index
            )
            self.cross_beam.add_features(cross_feature)
            self.features.append(cross_feature)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.elementdict[self.main_beam_guid]
        self.cross_beam = model.elementdict[self.cross_beam_guid]
