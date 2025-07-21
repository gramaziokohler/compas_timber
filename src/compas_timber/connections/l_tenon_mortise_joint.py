from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication.jack_cut import JackRafterCut
from compas_timber.fabrication.mortise import Mortise
from compas_timber.fabrication.tenon import Tenon

from .joint import JointTopology
from .tenon_mortise_joint import TenonMortiseJoint


class LTenonMortiseJoint(TenonMortiseJoint):
    """
    Represents a TenonMortise type joint which joins two beams, one of them at its end (main) and the other one along its centerline (cross) or both of them at their ends.
    A tenon is added on the main beam, and a corresponding mortise is made on the cross beam to fit the main beam's tenon.

    This joint type is compatible with beams in T and L topology.

    Please use `TenonMortiseJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined. This is the beam that will receive the tenon.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined. This is the beam that will receive the mortise.
    start_y : float, optional
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float, optional
        Depth of the tenon from the surface of the main beam.
    rotation : float, optional
        Rotation of the tenon around the main beam's axis.
    length : float, optional
        Length of the tenon.
    width : float, optional
        Width of the tenon.
    height : float, optional
        Height of the tenon.
    shape : int, optional
        The shape of the tenon, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float, optional
        The radius used to define the shape of the tenon, if applicable.


    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    main_beam_guid : str
        GUID of the main beam.
    cross_beam_guid : str
        GUID of the cross beam.
    start_y : float
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float
        Depth of the tenon from the surface of the main beam.
    rotation : float
        Rotation of the tenon around the main beam's axis.
    length : float
        Length of the tenon along the main beam.
    width : float
        Width of the tenon.
    height : float
        Height of the tenon.
    shape : int
        The shape of the tenon, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    features : list
        List of features or machining processings applied to the elements.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, main_beam, cross_beam, start_y=None, start_depth=None, rotation=None, length=None, width=None, height=None, shape=None, shape_radius=None, **kwargs):
        super(LTenonMortiseJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            start_y=start_y,
            start_depth=start_depth,
            rotation=rotation,
            length=length,
            width=width,
            height=height,
            shape=shape,
            shape_radius=shape_radius,
            **kwargs,
        )

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used

        # cross_beam
        try:
            cutting_plane = self.main_beam.front_side(self.main_beam_ref_side_index)
            start_cross, end_cross = self.cross_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        self.cross_beam.add_blank_extension(start_cross + extension_tolerance, end_cross + extension_tolerance, self.guid)
        # main_beam
        try:
            cutting_plane = self.cross_beam.opp_side(self.cross_beam_ref_side_index)
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        self.main_beam.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
            self.guid,
        )

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # generate  tenon features
        main_feature = Tenon.from_plane_and_beam(
            plane=self.cross_beam.ref_sides[self.cross_beam_ref_side_index],
            beam=self.main_beam,
            start_y=self.start_y,
            start_depth=self.start_depth,
            rotation=self.rotation,
            length=self.length,
            width=self.width,
            height=self.height,
            shape=self.tenon_shape,
            shape_radius=self.shape_radius,
            ref_side_index=self.main_beam_ref_side_index,
        )

        # generate mortise features
        cross_feature = Mortise.from_frame_and_beam(
            frame=main_feature.frame_from_params_and_beam(self.main_beam),
            beam=self.cross_beam,
            start_depth=0.0,  # TODO: to be updated once housing is implemented
            length=main_feature.length,
            width=main_feature.width,
            depth=main_feature.height,
            shape=main_feature.shape,
            shape_radius=main_feature.shape_radius,
            ref_side_index=self.cross_beam_ref_side_index,
        )

        modification_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
        cross_refinement_feature = JackRafterCut.from_plane_and_beam(modification_plane, self.cross_beam, self.cross_beam_ref_side_index)
        self.cross_beam.add_features(cross_refinement_feature)
        self.features.append(cross_refinement_feature)

        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features([cross_feature, cross_refinement_feature])
        # add features to joint
        self.features = [cross_feature, main_feature, cross_refinement_feature]
