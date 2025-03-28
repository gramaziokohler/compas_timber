from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon
from compas_timber.fabrication import TenonShapeType

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class TenonMortiseJoint(Joint):
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

    SUPPORTED_TOPOLOGY = [JointTopology.TOPO_T, JointTopology.TOPO_L]

    @property
    def __data__(self):
        data = super(TenonMortiseJoint, self).__data__
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
        **kwargs
    ):
        super(TenonMortiseJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.start_y = start_y
        self.start_depth = start_depth
        self.rotation = rotation
        self.length = length
        self.width = width
        self.height = height
        self.shape = shape
        self.shape_radius = shape_radius

        # assign default values if not provided
        self.set_default_values()

        self.features = []

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
        return ref_side_index

    @property
    def tenon_shape(self):
        if self.shape == 0:
            shape_type = TenonShapeType.AUTOMATIC
        elif self.shape == 1:
            shape_type = TenonShapeType.SQUARE
        elif self.shape == 2:
            shape_type = TenonShapeType.ROUND
        elif self.shape == 3:
            shape_type = TenonShapeType.ROUNDED
        elif self.shape == 4:
            shape_type = TenonShapeType.RADIUS
        else:
            raise ValueError("Invalid tenon shape index. Please provide a valid index between 0 and 4.")
        return shape_type

    def set_default_values(self):
        """Sets default values for attributes if they are not provided."""
        width, height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)
        # assign default values
        self.start_y = self.start_y or 0.0
        self.start_depth = self.start_depth or 0.0
        self.rotation = self.rotation or 0.0
        self.length = self.length or height
        self.width = self.width or width / 2
        self.height = self.height or width / 2
        self.shape = self.shape or 2  # Default shape: ROUND
        self.shape_radius = self.shape_radius or width / 4

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
            cutting_plane.translate(-cutting_plane.normal * self.height)
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

        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        # add features to joint
        self.features = [cross_feature, main_feature]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
