import math

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DovetailMortise
from compas_timber.fabrication import DovetailTenon
from compas_timber.fabrication import TenonShapeType

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector
from .utilities import point_centerline_towards_joint


class TDovetailJoint(Joint):
    """
    Represents a T-Dovetail type joint which joins two beams, one of them at its end (main) and the other one along its centerline (cross).
    A dovetail cut is made on the main beam, and a corresponding notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TDovetailJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    start_y : float
        Start position of the dovetail cut along the y-axis of the main beam.
    start_depth : float
        Depth of the dovetail cut from the surface of the main beam.
    rotation : float
        Rotation of the dovetail cut around the main beam's axis.
    length : float
        Length of the dovetail cut along the main beam.
    width : float
        Width of the dovetail cut.
    cone_angle : float
        The angle of the dovetail cut, determining the taper of the joint.
    dovetail_shape : int
        The shape of the dovetail cut, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    tool_angle : float
        The angle of the tool used to create the dovetail cut.
    tool_diameter : float
        The diameter of the tool used to create the dovetail cut.
    tool_height : float
        The height of the tool used to create the dovetail cut.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    start_y : float
        Start position of the dovetail cut along the y-axis of the main beam.
    start_depth : float
        Depth of the dovetail cut from the surface of the main beam.
    rotation : float
        Rotation of the dovetail cut around the main beam's axis.
    length : float
        Length of the dovetail cut along the main beam.
    width : float
        Width of the dovetail cut.
    cone_angle : float
        The angle of the dovetail cut, determining the taper of the joint.
    dovetail_shape : int
        The shape of the dovetail cut, represented by an integer index.
    tool_angle : float
        The angle of the tool used to create the dovetail cut.
    tool_diameter : float
        The diameter of the tool used to create the dovetail cut.
    tool_height : float
        The height of the tool used to create the dovetail cut.
    height : float, optional
        The height of the joint. This is not set during initialization but can be defined later.
    flank_angle : float, optional
        The angle of the flanks of the dovetail joint, if applicable.
    shape_radius : float, optional
        The radius used to define the shape of the joint, if applicable.
    features : list
        List of features or machining processings applied to the joint.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TDovetailJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["rotation"] = self.rotation
        data["length"] = self.length
        data["width"] = self.width
        data["cone_angle"] = self.cone_angle
        data["dovetail_shape"] = self.dovetail_shape
        data["tool_angle"] = self.tool_angle
        data["tool_diameter"] = self.tool_diameter
        data["tool_height"] = self.tool_height
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
        cone_angle=None,
        dovetail_shape=None,
        tool_angle=None,
        tool_diameter=None,
        tool_height=None,
        **kwargs
    ):
        super(TDovetailJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        # Default values if not provided
        self.start_y = start_y if start_y is not None else 0.0
        self.start_depth = start_depth if start_depth is not None else 0.0
        self.rotation = rotation if rotation is not None else 0.0
        self.length = length if length is not None else 60.0
        self.width = width if width is not None else 25.0
        self.cone_angle = cone_angle if cone_angle is not None else 10.0
        self.dovetail_shape = dovetail_shape if dovetail_shape is not None else 4  # shape: RADIUS

        self.tool_angle = tool_angle if tool_angle is not None else 15.0
        self.tool_diameter = tool_diameter if tool_diameter is not None else 60.0
        self.tool_height = tool_height if tool_height is not None else 28.0

        self.height = None
        self.flank_angle = None
        self.shape_radius = None

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
        # get the vector towards the joint
        centerline_vect = point_centerline_towards_joint(self.main_beam, self.cross_beam)
        # flip the vector if the dot product with the y-axis of the reference side is negative
        vector = self.cross_beam.ref_sides[self.cross_beam_ref_side_index].yaxis
        if centerline_vect.dot(vector) < 0:
            vector = -vector
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, vector, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def shape(self):
        if self.dovetail_shape == 0:
            shape_type = TenonShapeType.AUTOMATIC
        elif self.dovetail_shape == 1:
            shape_type = TenonShapeType.SQUARE
        elif self.dovetail_shape == 2:
            shape_type = TenonShapeType.ROUND
        elif self.dovetail_shape == 3:
            shape_type = TenonShapeType.ROUNDED
        elif self.dovetail_shape == 4:
            shape_type = TenonShapeType.RADIUS
        else:
            raise ValueError("Invalid tenon shape index. Please provide a valid index between 0 and 4.")
        return shape_type

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
            cutting_plane.translate(-cutting_plane.normal * self.tool_height)
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
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # define the tool parameters
        self.define_dovetail_tool(self.tool_angle, self.tool_diameter, self.tool_height)

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
            cone_angle=self.cone_angle,
            flank_angle=self.flank_angle,
            shape=self.shape,
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

        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        # add features to joint
        self.features = [cross_feature, main_feature]

    def define_dovetail_tool(self, tool_angle, tool_diameter, tool_height):
        """Define the parameters for the dovetail feature based on a defined dovetail cutting tool.

        Parameters
        ----------
        tool_angle : float
            The angle of the dovetail cutter tool.
        tool_diameter : float
            The diameter of the dovetail cutter tool.
        tool_height : float
            The height of the dovetail cutter tool.

        """
        # type: (float, float, float) -> None
        # get the tool parameters
        tool_top_radius = tool_diameter / 2 - tool_height * (math.tan(math.radians(tool_angle)))
        # define parameters related to the tool if a tool is defined
        self.height = tool_height
        self.flank_angle = tool_angle
        self.shape_radius = tool_top_radius

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
