from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DovetailMortise
from compas_timber.fabrication import DovetailTenon
from compas_timber.fabrication.jack_cut import JackRafterCut

from .solver import JointTopology
from .tenon_mortise_joint import TenonMortiseJoint


class LDovetailJoint(TenonMortiseJoint):
    """
    Represents a T-Dovetail type joint which joins two beams, one of them at its end (main) and the other one along its centerline (cross).
    A dovetail tenon is added on the main beam, and a corresponding dovetail mortse is made on the cross beam to fit the main beam's tenon.

    This joint type is compatible with beams in T topology.

    Please use `TDovetailJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined. This is the beam that will receive the dovetail tenon.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined. This is the beam that will receive the dovetail mortise.
    start_y : float, optional
        Start position of the dovetail tenon along the y-axis of the main beam.
    start_depth : float, optional
        Depth of the dovetail tenon from the surface of the main beam.
    rotation : float, optional
        Rotation of the dovetail tenon around the main beam's axis.
    length : float, optional
        Length of the dovetail tenon.
    width : float, optional
        Width of the dovetail tenon.
    height : float, optional
        Height of the dovetail tenon, which is typically defined by the tool used to create the cut.
    shape : int, optional
        The shape of the dovetail cut, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float, optional
        The radius used to define the shape of the tenon, if applicable.
    dovetail_tool : dict, optional
        A dictionary containing the parameters of the dovetail tool used to create the cut. It should contain the following keys:
        - 'angle': float, the angle of the tool used to create the dovetail cut.
        - 'diameter': float, the diameter of the tool used to create the dovetail cut.
        - 'height': float, the height of the tool used to create the dovetail cut.


    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined. This is the beam that will receive the dovetail tenon.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined. This is the beam that will receive the dovetail mortise
    main_beam_guid : str
        GUID of the main beam.
    cross_beam_guid : str
        GUID of the cross beam.
    start_y : float
        Start position of the dovetail tenon along the y-axis of the main beam.
    start_depth : float
        Depth of the dovetail tenon from the surface of the main beam.
    rotation : float
        Rotation of the dovetail tenon around the main beam's axis.
    length : float
        Length of the dovetail tenon.
    width : float
        Width of the dovetail tenon.
    height : float, optional
        Height of the dovetail tenon, which is typically defined by the tool used to create the cut.
    shape : int
        The shape of the dovetail cut, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    dovetail_tool : dict, optional
        A dictionary containing the parameters of the dovetail tool used to create the cut. It should contain the following keys:
        - 'angle': float, the angle of the tool used to create the dovetail cut.
        - 'diameter': float, the diameter of the tool used to create the dovetail cut.
        - 'height': float, the height of the tool used to
    features : list
        List of features added to the main and cross beams for the dovetail joint.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    _DEFAULT_DOVETAIL_TOOL = {
        "angle": 15.0,
        "diameter": 60.0,
        "height": 28.0,
    }

    @property
    def __data__(self):
        data = super(LDovetailJoint, self).__data__
        data["dovetail_tool"] = self.dovetail_tool
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        start_y=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        height=None,
        shape=None,
        shape_radius=None,
        dovetail_tool=None,
        **kwargs
    ):
        super(LDovetailJoint, self).__init__(
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
            dovetail_tool=dovetail_tool,
            **kwargs
        )

        # store dovetail-specific parameters
        self.dovetail_tool = dovetail_tool or self._DEFAULT_DOVETAIL_TOOL
        if not isinstance(self.dovetail_tool, dict) or set(self.dovetail_tool.keys()) != {"angle", "diameter", "height"}:
            raise ValueError("dovetail_tool must be a dict with keys 'angle', 'diameter', 'height'.")

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

        # define dovetail tool
        DovetailTenon.define_dovetail_tool(*[self.dovetail_tool[key] for key in ['angle', 'diameter', 'height']]) # TODO: use .values() in v2.0 (post-IronPython)

        # generate dovetail tenon features
        main_feature = DovetailTenon.from_plane_and_beam(
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

        # generate dovetail mortise features
        cross_feature = DovetailMortise.from_frame_and_beam(
            frame=main_feature.frame_from_params_and_beam(self.main_beam),
            beam=self.cross_beam,
            start_depth=0.0,  # TODO: to be updated once housing is implemented
            angle=self.rotation,
            length=main_feature.length,
            width=main_feature.width,
            depth=main_feature.height,
            cone_angle=main_feature.cone_angle,
            flank_angle=main_feature.flank_angle,
            shape=main_feature.shape,
            shape_radius=main_feature.shape_radius,
            ref_side_index=self.cross_beam_ref_side_index,
        )

        # generate refinement features
        modification_plane = self.main_beam.front_side(self.main_beam_ref_side_index)
        cross_refinement_feature = JackRafterCut.from_plane_and_beam(modification_plane, self.cross_beam, self.cross_beam_ref_side_index)

        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features([cross_feature, cross_refinement_feature])
        # add features to joint
        self.features = [cross_feature, main_feature, cross_refinement_feature]
