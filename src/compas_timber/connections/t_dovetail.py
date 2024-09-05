import math

from compas_timber._fabrication import DovetailMortise
from compas_timber._fabrication import DovetailTenon

from compas_timber._fabrication.btlx_process import TenonShapeType

from compas.geometry import Plane, intersection_line_plane, Line, distance_point_point

from .joint import Joint
from .solver import JointTopology


class TDovetailJoint(Joint):
    """Represents an T-Step type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).
    Two or more cuts are is made on the main beam and a notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TStepJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TDovetailJoint, self).__data__
        data["main_beam"] = self.main_beam_guid
        data["cross_beam"] = self.cross_beam_guid
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

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        cone_angle=None,
        dovetail_shape=None,
        tool_angle=None,
        tool_diameter=None,
        tool_height=None,
    ):
        super(TDovetailJoint, self).__init__()
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None

        self.start_depth = start_depth
        self.rotation = rotation
        self.length = length
        self.width = width
        self.cone_angle = cone_angle
        self.dovetail_shape = dovetail_shape

        self.tool_angle = tool_angle
        self.tool_diameter = tool_diameter
        self.tool_height = tool_height

        self.height = None
        self.flank_angle = None
        self.shape_radius = None

        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = self._beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = self._get_ref_side_most_ortho_to_cross_vector(self.cross_beam, self.main_beam, ignore_ends=True)
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

        main_beam_ref_side = self.main_beam.ref_sides[self.main_beam_ref_side_index]
        cross_beam_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]

        print("main_beam_ref_side", self.main_beam_ref_side_index)
        print("cross_beam_ref_side", self.cross_beam_ref_side_index)

        # generate dovetail tenon features
        main_feature = DovetailTenon.from_plane_and_beam(
            cross_beam_ref_side,
            self.main_beam,
            self.start_depth,
            self.rotation,
            self.length,
            self.width,
            self.height,
            self.cone_angle,
            self.flank_angle,
            self.shape,
            self.shape_radius,
            self.main_beam_ref_side_index,
        )

        # generate dovetail mortise features
        cross_feature = DovetailMortise.from_plane_tenon_and_beam(
            main_feature.frame_from_params_and_beam(self.main_beam),
            main_feature,
            self.cross_beam,
            self.cross_beam_ref_side_index,
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
        # update parameters related to the tool if a tool is defined
        self.height = tool_height
        self.flank_angle = tool_angle
        self.shape_radius = tool_top_radius

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.elementdict[self.main_beam_guid]
        self.cross_beam = model.elementdict[self.cross_beam_guid]
