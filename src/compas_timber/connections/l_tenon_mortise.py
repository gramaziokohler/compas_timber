from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon

from .solver import JointTopology
from .tenon_mortise import TenonMortiseJoint


class LTenonMortiseJoint(TenonMortiseJoint):
    """
    Represents a TenonMortise type joint which joins two beams, one of them at its end (main) and the other one along its centerline (cross) or both of them at their ends.
    A tenon is added on the main beam, and a corresponding mortise is made on the cross beam to fit the main beam's tenon.

    This joint type is compatible with beams in T and L topology.

    Please use `TenonMortiseJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
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

    @property
    def __data__(self):
        data = super(LTenonMortiseJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["rotation"] = self.rotation
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["shape"] = self.shape
        data["shape_radius"] = self.shape_radius
        data["modify_cross"] = self.modify_cross

        return data

    # fmt: off
    def __init__(
        self,
        main_beam,
        cross_beam,
        start_y=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        height=None,
        shape=None,
        shape_radius=None,
        modify_cross=False,
        **kwargs
    ):
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
            **kwargs
        )
        self.modify_cross = modify_cross

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

        #cross_beam
        try:
            cutting_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
            start_cross, end_cross = self.cross_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        self.cross_beam.add_blank_extension(
            start_cross + extension_tolerance,
            end_cross + extension_tolerance,
            self.guid
            )
        #main_beam
        try:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            main_width = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[0]
            offset = self.height or main_width / 2    # in case height is not set this is the default value set when adding features
            cutting_plane.translate(-cutting_plane.normal * offset)
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

        # set default values if not provided
        self._update_unset_values()

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

        self.main_beam.add_features(main_feature)
        self.features = [main_feature]

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

        cross_features = [cross_feature]

        # generate cross cut_off feature
        if self.modify_cross:
            cutting_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
            cross_cutoff_feature = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.cross_beam)
            cross_features.append(cross_cutoff_feature)

        self.cross_beam.add_features(cross_features)
        self.features.extend(cross_features)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
