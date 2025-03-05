import math

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import NurbsCurve
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point_sqrd
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_segment
from compas.geometry import intersection_segment_segment
from compas.geometry import matrix_from_frame_to_frame
from compas.geometry import offset_line
from compas.tolerance import TOL

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import InterfaceLocation
from compas_timber.connections import InterfaceRole
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.elements import OpeningType
from compas_timber.elements import Plate
from compas_timber.elements.features import BrepSubtraction

from .workflow import JointDefinition


class WallSelector(object):
    """Selects walls based on their attributes."""

    def __init__(self, wall_attr, attr_vlaue):
        self._wall_attr = wall_attr
        self._attr_value = attr_vlaue

    def select(self, wall):
        value = getattr(wall, self._wall_attr, None)
        if value is None:
            return False
        else:
            return value == self._attr_value


class AnyWallSelector(object):
    def select(self, _):
        return True


class WallToWallInterface(object):
    """

    Parameters
    ----------
    face : :class:`compas.geometry.PlanarSurface`
        Planar surface representing the portion of the wall which touches the other wall.
        The face's normal points towards the other wall.
    topology : :class:`compas_timber.connections.JointTopology`
        The topology of the joint between the two walls.

    """

    def __init__(self, face, topology):
        self.face = face
        self.topology = topology


class BeamDefinition(object):
    """
    TODO: Move this to a separate module (potentially into workflow.py)

    Container for Beam attributes before beam is instantiated.

    Parameters
    ----------
    centerline : :class:`compas.geometry.Line`
        The centerline of the beam.
    width : float, optional
        The width of the beam.
    height : float, optional
        The height of the beam.
    z_axis : :class:`compas.geometry.Vector`, optional
        The z axis of the beam.
    normal : :class:`compas.geometry.Vector`, optional
        The normal of the beam.
    type : str, optional
        The type of the beam.
    polyline : :class:`compas.geometry.Polyline`, optional
        The polyline of the beam.
    parent : :class:`compas_timber.model.SurfaceAssembly` or :class:`compas_timber.model.SurfaceAssembly.Window`
        The parent of the beam.

    Attributes
    ----------
    centerline : :class:`compas.geometry.Line`
        The centerline of the beam element.
    width : float
        The width of the beam element.
    height : float
        The height of the beam element.
    z_axis : :class:`compas.geometry.Vector`
        The z axis of the parent (Not the Beam).
    normal : :class:`compas.geometry.Vector`
        The normal of the parent.


    """

    def __init__(
        self,
        centerline,
        width=None,
        height=None,
        z_axis=None,  # TODO: remove
        normal=None,
        type=None,
        parent=None,
    ):
        self.original_centerline = centerline
        self.centerline = Line(centerline[0], centerline[1])
        self._width = width
        self._height = height
        self._normal = normal
        self.type = type
        self.parent = parent  # TODO: remove

    def __repr__(self):
        return "BeamDefinition({}, {}, {}, {})".format(self.centerline, self.width, self.height, self.type)

    @property
    def width(self):
        # TODO: provide this upon creation
        return self._width if self._width else self.parent.beam_dimensions[self.type][0]

    @property
    def height(self):
        # TODO: provide this upon creation
        return self._height if self._height else self.parent.beam_dimensions[self.type][1]

    @property
    def z_aligned_centerline(self):
        # TODO: provide this upon creation
        if dot_vectors(self.centerline.direction, self.parent.z_axis) < 0:
            return Line(self.centerline.end, self.centerline.start)
        else:
            return self.centerline

    @property
    def normal(self):
        # TODO: provide this upon creation
        return self._normal if self._normal else self.parent.normal

    def offset(self, distance, reverse_dir=False):
        normal = self.normal if not reverse_dir else -self.normal
        line = offset_line(self.centerline, distance, normal)
        self.centerline = Line(line[0], line[1])

    def translate(self, vector):
        self.centerline.transform(vector)

    def to_beam(self):
        # TODO: this is quite stiff, if I know the corner, I can just create beam using Beam(...)
        centerline = Line(*self.centerline)
        centerline.translate(self.normal * 0.5 * self.height)
        beam = Beam.from_centerline(centerline, self.width, self.height, self.normal)
        beam.name = "{}_{}".format(self.type, beam.guid)
        beam.attributes["category"] = self.type
        return beam

    def set_centerline(self, line):
        self.centerline = line


class Window(object):
    """

    # TODO: is this an Element maybe?

    A window object for the SurfaceAssembly.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the window.
    sill_height : float, optional
        The height of the sill.
    header_height : float, optional
        The height of the header.
    parent : :class:`compas_timber.model.SurfaceAssembly`
        The parent of the window.

    Attributes
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the window.
    sill_height : float
        The height of the sill.
    header_height : float
        The height of the header.
    parent : :class:`compas_timber.model.SurfaceAssembly`
        The parent of the window.
    z_axis : :class:`compas.geometry.Vector`
        The z axis of the parent.
    normal : :class:`compas.geometry.Vector`
        The normal of the parent.
    beam_dimensions : dict
        The beam dimensions of the parent.
    beam_definions : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The beam_definions of the window.
    length : float
        The length of the window.
    height : float
        The height of the window.
    frame : :class:`compas.geometry.Frame`
        The frame of the window.

    """

    def __init__(self, outline, beam_dimensions, wall_frame, wall_thickness, tolerance, sheeting_inside=None, sheeting_outside=None, lintel_posts=None):
        self.beam_dimensions = beam_dimensions
        self._wall_frame = wall_frame
        self._sheeting_inside = sheeting_inside
        self._sheeting_outside = sheeting_outside
        self._lintel_posts = lintel_posts
        self._wall_thickness = wall_thickness
        self.outline = outline
        self.sill_height = self.beam_dimensions["sill"][0]
        self.header_height = self.beam_dimensions["header"][0]
        self.z_axis = self._wall_frame.yaxis
        self.normal = self._wall_frame.zaxis
        self._beam_definitions = []
        self._length = None
        self._height = None
        self._frame = None
        self.dist_tolerance = tolerance

    @property
    def jack_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "jack_stud"]

    @property
    def sills(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "sill"]

    @property
    def headers(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "header"]

    @property
    def length(self):
        if not self._length:
            _ = self.frame
        return self._length

    @property
    def height(self):
        if not self._height:
            _ = self.frame
        return self._height

    @property
    def frame(self):
        # if not self._frame:
        #     self._frame, self._panel_length, self._panel_height = get_frame(self.points, self.parent.normal, self.zaxis)
        return self._frame

    @property
    def boolean_feature(self):
        offset = self._sheeting_inside if self._sheeting_inside else 0
        so = self._sheeting_outside if self._sheeting_outside else 0
        thickness = offset + so + self._wall_thickness

        crv = self.outline.copy()
        crv.translate(self.normal * -offset)

        vol = Brep.from_extrusion(NurbsCurve.from_points(crv.points, degree=1), self.normal * thickness)

        # negative volume will cause weird boolean result
        if vol.volume < 0:
            # TODO: remove once this is release in compas core
            if hasattr(vol, "flip"):
                vol.flip()

        return BrepSubtraction(vol)

    def create_elements(self):
        # ^  3 ---- 2
        # |  |      |
        # z  0 ---- 1
        #    x -->
        top_segment = self.outline.lines[2]
        bottom_segment = self.outline.lines[0]
        left_segment = self.outline.lines[3]
        right_segment = self.outline.lines[1]

        header = BeamDefinition(top_segment, parent=self, type="header")
        sill = BeamDefinition(bottom_segment, parent=self, type="sill")

        stud_roles = "jack_stud" if self._lintel_posts else "king_stud"
        studs = []
        studs.append(BeamDefinition(left_segment, parent=self, type=stud_roles))
        studs.append(BeamDefinition(right_segment, parent=self, type=stud_roles))

        beam_definitions = [header, sill] + studs

        offset_elements(beam_definitions, offset_inside=False)

        shorten_edges_to_fit_between_plates(studs, [header, sill])

        if self._lintel_posts:
            for beam_def in self.jack_studs:
                offset = (self.beam_dimensions["jack_stud"][0] + self.beam_dimensions["king_stud"][0]) / 2
                king_line = offset_line(beam_def.centerline, offset, self.normal)
                beam_definitions.append(BeamDefinition(king_line, type="king_stud", parent=self))
        return beam_definitions


class Door(Window):
    """TODO: revise when we know where this is going, maybe no need for classes here beyond Opening"""

    def __init__(self, outline, beam_dimensions, wall_frame, wall_thickness, tolerance, sheeting_inside=None, sheeting_outside=None, lintel_posts=None):
        super(Door, self).__init__(outline, beam_dimensions, wall_frame, wall_thickness, tolerance, sheeting_inside, sheeting_outside, lintel_posts)

    def create_elements(self):
        elements = super(Door, self).create_elements()
        return [e for e in elements if e.type != "sill"]


class WallPopulatorConfigurationSet(object):
    """Contains one or more configuration set for the WallPopulator.

    wall_selector can be used to apply different configurations to different walls based on e.g. their name.

    Parameters
    ----------
    stud_spacing : float
        Space between the studs.
    beam_width : float
        Width of the beams.
    tolerance : :class:`compas_tolerances.Tolerance`, optional
        The tolerance for the populator.
    sheeting_outside : float, optional
        The thickness of the sheeting outside.
    sheeting_inside : float, optional
        The thickness of the sheeting inside.
    lintel_posts : bool, optional
        Whether to use lintel posts.
    edge_stud_offset : float, optional
        Additional offset for the edge studs.
    custom_dimensions : dict, optional
        Custom cross section for the beams, by category. (e.g. {"king_stud": (120, 60)})
    joint_overrides : list(`compas_timber.workflow.CategoryRule), optional
        List of joint rules to override the default ones.
    connection_details : dict, optional
        Mapping of `JointTopology` to and instace of ConnectionDetail class.

    """

    def __init__(
        self,
        stud_spacing,
        beam_width,
        z_axis=None,
        tolerance=None,
        sheeting_outside=None,
        sheeting_inside=None,
        lintel_posts=True,
        edge_stud_offset=0.0,
        custom_dimensions=None,
        joint_overrides=None,
        wall_selector=None,
        connection_details=None,
    ):
        self.stud_spacing = stud_spacing
        self.beam_width = beam_width
        self.z_axis = z_axis or Vector.Zaxis()
        self.tolerance = tolerance or TOL
        self.sheeting_outside = sheeting_outside
        self.sheeting_inside = sheeting_inside
        self.lintel_posts = lintel_posts
        self.edge_stud_offset = edge_stud_offset or 0.0
        self.custom_dimensions = custom_dimensions
        self.joint_overrides = joint_overrides
        self.wall_selector = wall_selector or AnyWallSelector()
        self.connection_details = connection_details or {}

    def __str__(self):
        return "WallPopulatorConfigurationSet({}, {}, {})".format(self.stud_spacing, self.beam_width, self.z_axis)

    @classmethod
    def default(cls, stud_spacing, beam_width):
        return cls(stud_spacing, beam_width)


class WallPopulator(object):
    """Create a timber assembly from a surface.

    Parameters
    ----------
    configuration_set : :class:`WallPopulatorConfigurationSet`
        The configuration for this wall populator.
    wall : :class:`compas_timber.elements.Wall`
        The wall for this populater to fill with beams.
    interfaces : optional, list of :class:`WallToWallInterface`
        The interfaces of the wall.

    Attributes
    ----------
    beams : list of :class:`compas_timber.elements.Beam`
        The beams of the assembly.
    rules : list of :class:`compas_timber.design.CategoryRule`
        The rules for the assembly.
    centerlines : list of :class:`compas.geometry.Line`
        The centerlines of the beams.
    normal : :class:`compas.geometry.Vector`
        The normal of the surface.
    panel_length : float
        The length of the panel.
    panel_height : float
        The height of the panel.
    frame : :class:`compas.geometry.Frame`
        The frame of the assembly.
    jack_studs : list of :class:`BeamDefinition`
        The jack studs of the assembly.
    king_studs : list of :class:`BeamDefinition`
        The king studs of the assembly.
    edge_studs : list of :class:`BeamDefinition`
        The edge studs of the assembly.
    studs : list of :class:`BeamDefinition`
        The studs of the assembly.
    sills : list of :class:`BeamDefinition`
        The sills of the assembly.
    headers : list of :class:`BeamDefinition`
        The headers of the assembly.
    plates : list of :class:`BeamDefinition`

    """

    BEAM_CATEGORY_NAMES = ["stud", "king_stud", "jack_stud", "edge_stud", "plate", "header", "sill", "detail"]

    def __init__(self, configuration_set, wall, interfaces=None):
        self._wall = wall
        self._config_set = configuration_set
        self._z_axis = wall.frame.yaxis  # up
        self.normal = wall.frame.zaxis  # out
        self.outer_polyline = wall.outline
        self.inner_polylines = wall.openings
        self.edges = []
        self._elements = []
        self._beam_definitions = []
        self._rules = []
        self._features = []
        self.beam_dimensions = {}
        self.dist_tolerance = configuration_set.tolerance.relative

        self.frame = wall.frame
        self.panel_length = wall.length
        self.panel_height = wall.height

        self._interfaces = interfaces or []
        self._adjusted_segments = {}
        self._plate_segments = {}
        self._detail_obbs = []
        self._openings = []

        for key in self.BEAM_CATEGORY_NAMES:
            self.beam_dimensions[key] = (configuration_set.beam_width, wall.thickness)

        if self._config_set.custom_dimensions:
            dimensions = self._config_set.custom_dimensions
            for key, value in dimensions.items():
                if value:
                    self.beam_dimensions[key] = value

    def __repr__(self):
        return "WallPopulator({}, {})".format(self._config_set, self._wall)

    @property
    def z_axis(self):
        cross = cross_vectors(self.normal, self._z_axis)
        return Vector(*cross_vectors(cross, self.normal))

    @property
    def default_rules(self):
        edge_plate_joint = LButtJoint if TOL.is_zero(self._config_set.edge_stud_offset) else TButtJoint
        return [
            CategoryRule(edge_plate_joint, "edge_stud", "plate"),
            CategoryRule(TButtJoint, "detail", "plate"),  # TODO: have the details define this
            CategoryRule(LButtJoint, "detail_edge", "plate"),  # TODO: have the details define this
            CategoryRule(TButtJoint, "stud", "plate"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "stud", "sill"),
            CategoryRule(LButtJoint, "jack_stud", "plate"),
            CategoryRule(TButtJoint, "jack_stud", "plate"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "plate"),
            CategoryRule(LButtJoint, "king_stud", "plate"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "sill", "jack_stud"),
        ]

    @property
    def rules(self):
        if not self._rules:
            self._rules = self.default_rules
            if self._config_set.joint_overrides:
                for rule in self._config_set.joint_overrides:
                    rule_set = set([rule.category_a, rule.category_b])
                    for i, _rule in enumerate(self._rules):
                        _set = set([_rule.category_a, _rule.category_b])
                        if rule_set == _set:
                            self._rules[i] = rule
                            break
        return self._rules

    @property
    def centerlines(self):
        return [beam_def.centerline for beam_def in self.beam_definitions]

    @property
    def elements(self):
        elements = []
        for beam_def in self._beam_definitions:
            try:
                elements.append(beam_def.to_beam())
            except Exception:
                print("Error creating beam from centerline: {}".format(beam_def.centerline))
                print("Beam role is: {}".format(beam_def.type))
        elements.extend(self._elements)
        return elements

    @property
    def features(self):
        return self._features

    @property
    def plate_elements(self):
        for plate in self._elements:
            if isinstance(plate, Plate):
                yield plate

    @property
    def points(self):
        return self.outer_polyline.points

    @property
    def jack_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "jack_stud"]

    @property
    def king_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "king_stud"]

    @property
    def edge_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "edge_stud"]

    @property
    def studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "stud"]

    @property
    def sills(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "sill"]

    @property
    def headers(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "header"]

    @property
    def plates(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "plate"]

    @classmethod
    def beam_category_names(cls):
        return WallPopulator.BEAM_CATEGORY_NAMES

    @classmethod
    def from_model(cls, model, configuration_sets):
        # type: (TimberModel, List[WallPopulatorConfigurationSet]) -> List[WallPopulator]
        """matches configuration sets to walls and returns a list of WallPopulator instances, each per wall"""
        # TODO: make sure number of walls and configuration sets match
        walls = list(model.slabs)  # TODO: these are anoying, consider making these lists again
        if len(walls) != len(configuration_sets):
            raise ValueError("Number of walls and configuration sets do not match")

        wall_populators = []
        for wall in walls:
            for config_set in configuration_sets:
                if config_set.wall_selector.select(wall):
                    interfaces = [interaction.get_interface_for_wall(wall) for interaction in model.get_interactions_for_element(wall)]
                    wall_populators.append(cls(config_set, wall, interfaces))
                    break
        return wall_populators

    def create_elements(self):
        """Does the actual populating of the wall

        creates and returns all the elements in the wall, returns also the joint definitions
        """
        self.generate_perimeter_beams()
        self.generate_openings()
        self.generate_studs()
        self.generate_plates()
        elements = self.elements
        return elements

    def create_joint_definitions(self, elements, max_distance=None):
        beams = [element for element in elements if element.is_beam]
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(beams, rtree=True, max_distance=self.dist_tolerance)

        joint_definitions = []
        max_distance = max_distance or 0.0
        max_distance = max(self._config_set.beam_width, max_distance)  # oterwise L's become X's
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=max_distance)
            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue

            for rule in self.rules:
                if rule.comply(pair, model_max_distance=max_distance) and rule.joint_type.SUPPORTED_TOPOLOGY == detected_topo:
                    if rule.joint_type == LButtJoint:
                        beam_a, beam_b = rule.reorder([beam_a, beam_b])
                    joint_definitions.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
                    # break # ?
        return joint_definitions

    def generate_perimeter_beams(self):
        # for each interface, find the appropriate connection detail (depending on the topology)
        # first the interfaces are handled, then the remaining sides are handled by the default connection details
        handled_sides = set()

        # TODO: move to Wall
        # add any remaining sides if have not been handled by any of the connection details
        # ^  3 ---- 2
        # |  |      |
        # z  0 ---- 1
        #    x -->
        front_segment = Line(self.points[1], self.points[2])
        back_segment = Line(self.points[3], self.points[0])
        top_segment = Line(self.points[2], self.points[3])
        bottom_segment = Line(self.points[0], self.points[1])
        self._adjusted_segments = {"front": front_segment, "back": back_segment, "top": top_segment, "bottom": bottom_segment}

        perimeter_beams = []
        for interface in self._interfaces:
            connection_detail = self._config_set.connection_details.get(interface.topology, None)

            if connection_detail:
                if interface.interface_role == InterfaceRole.MAIN:
                    perimeter_beams.extend(connection_detail.create_elements_main(interface, self._wall, self._config_set))
                    connection_detail.adjust_segments_main(interface, self._wall, self._config_set, self._adjusted_segments)
                elif interface.interface_role == InterfaceRole.CROSS:
                    connection_detail.adjust_segments_cross(interface, self._wall, self._config_set, self._adjusted_segments)
                    perimeter_beams.extend(connection_detail.create_elements_cross(interface, self._wall, self._config_set))

                handled_sides.add(interface.interface_type)

        top_segment = self._adjusted_segments["top"]
        bottom_segment = self._adjusted_segments["bottom"]
        front_segment = self._adjusted_segments["front"]
        back_segment = self._adjusted_segments["back"]

        if InterfaceLocation.FRONT not in handled_sides:
            perimeter_beams.append(BeamDefinition(front_segment, parent=self, type="edge_stud"))

        if InterfaceLocation.BACK not in handled_sides:
            perimeter_beams.append(BeamDefinition(back_segment, parent=self, type="edge_stud"))

        if InterfaceLocation.TOP not in handled_sides:
            perimeter_beams.append(BeamDefinition(top_segment, parent=self, type="plate"))

        if InterfaceLocation.BOTTOM not in handled_sides:
            perimeter_beams.append(BeamDefinition(bottom_segment, parent=self, type="plate"))

        edge_studs = [beam_def for beam_def in perimeter_beams if beam_def.type == "edge_stud"]
        plate_beams = [beam_def for beam_def in perimeter_beams if beam_def.type == "plate"]

        if self._wall.is_wall:
            offset_elements(edge_studs + plate_beams)
        else:
            # HACK alert! slabs seem to want it differently, get to the bottom of this
            if self.normal.z < 0:
                offset_elements(edge_studs + plate_beams, offset_inside=False)
            else:
                offset_elements(edge_studs + plate_beams)

        shorten_edges_to_fit_between_plates(edge_studs, plate_beams, self.dist_tolerance)

        self._beam_definitions.extend(perimeter_beams)

        # TODO: handle lintel posts

    def get_interior_segment_indices(self, polyline):
        points = polyline.points[0:-1]
        out = []
        for index in range(len(points)):
            if index == 0:
                angle = angle_vectors_signed(points[-1] - points[0], points[1] - points[0], self.normal, deg=True)
            elif index == len(points) - 1:
                angle = angle_vectors_signed(points[-2] - points[-1], points[0] - points[-1], self.normal, deg=True)
            else:
                angle = angle_vectors_signed(points[index - 1] - points[index], points[index + 1] - points[index], self.normal, deg=True)
            if angle > 0:
                out.append(index)
        if len(out) > 0:
            out.insert(0, out[0] - 1)
        return set(out)

    def generate_openings(self):
        for opening in self.inner_polylines:
            if opening.opening_type == OpeningType.DOOR:
                element = Door(
                    opening.polyline,
                    self.beam_dimensions,
                    self._wall.frame,
                    self._wall.thickness,
                    self.dist_tolerance,
                    self._config_set.sheeting_inside,
                    self._config_set.sheeting_outside,
                    # self._config_set.lintel_posts,
                )
            else:
                element = Window(
                    opening.polyline,
                    self.beam_dimensions,
                    self._wall.frame,
                    self._wall.thickness,
                    self.dist_tolerance,
                    self._config_set.sheeting_inside,
                    self._config_set.sheeting_outside,
                    # self._config_set.lintel_posts,
                )

            self._beam_definitions.extend(element.create_elements())
            self._openings.append(element)

    def generate_studs(self):
        self.generate_stud_lines()
        self.trim_jack_studs()
        self.trim_king_studs()
        self.trim_studs()
        self.cull_overlaps()

    def generate_stud_lines(self):
        x_position = self._config_set.stud_spacing
        while x_position < self.panel_length - self._config_set.beam_width:
            start_point = Point(x_position, 0, 0)
            start_point.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            line = Line.from_point_and_vector(start_point, self.z_axis * self.panel_height)
            self._beam_definitions.append(BeamDefinition(line, type="stud", parent=self))
            x_position += self._config_set.stud_spacing

    def get_beam_intersections(self, beam_def, *element_lists_to_intersect):
        intersections = []
        dots = []
        for element_list in element_lists_to_intersect:
            for element_to_intersect in element_list:
                point = intersection_line_segment(beam_def.z_aligned_centerline, element_to_intersect.centerline, 0.01)[0]
                if point:
                    intersections.append(point)
        if len(intersections) > 1:
            intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            dots = [dot_vectors(Vector.from_start_end(beam_def.z_aligned_centerline.start, x), self.z_axis) / beam_def.centerline.length for x in intersections]
        return intersections, dots

    def trim_jack_studs(self):
        for beam_def in self.jack_studs:
            intersections, dots = self.get_beam_intersections(beam_def, self.plates, self.headers)
            if len(intersections) > 1:
                bottom = None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                top = beam_def.z_aligned_centerline.end
                if not bottom:
                    bottom = beam_def.z_aligned_centerline.start
            beam_def.set_centerline(Line(bottom, top))

    def trim_king_studs(self):
        for beam_def in self.king_studs:
            intersections, dots = self.get_beam_intersections(beam_def, self.plates, self.headers, self.sills)
            if len(intersections) > 1:
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < -0.01:
                        bottom = intersections[i]  # last intersection below sill
                    if dot > 1.01:
                        top = intersections[i]  # first intersection above header
                        break
                if not bottom:
                    bottom = beam_def.z_aligned_centerline.start
                if not top:
                    top = beam_def.z_aligned_centerline.end
                beam_def.set_centerline(Line(bottom, top))

    def trim_studs(self):
        stud_elements = []
        while len(self.studs) > 0:
            for beam_def in self._beam_definitions:
                if beam_def.type == "stud":
                    intersections, _ = self.get_beam_intersections(beam_def, self.plates, self.headers, self.sills)
                    while len(intersections) > 1:
                        top = intersections.pop()
                        bottom = intersections.pop()
                        stud_elements.append(BeamDefinition(Line(bottom, top), type="stud", parent=self))
                    self._beam_definitions.remove(beam_def)
        self._beam_definitions.extend(stud_elements)

    def cull_overlaps(self):
        studs = self.studs
        for beam_def in studs:
            for other_element in self.king_studs + self.jack_studs + self.edge_studs:
                if self.distance_between_elements(beam_def, other_element) < (self.beam_dimensions[beam_def.type][0] + self.beam_dimensions[other_element.type][0]) / 2:
                    self._beam_definitions.remove(beam_def)
                    break

        # removed studs that are inside details
        for beam_def in studs:
            for interface in self._interfaces:
                detail = self._config_set.connection_details.get(interface.topology, None)
                if not detail:
                    continue

                if interface.interface_role == InterfaceRole.MAIN:
                    detail_obb = detail.get_detail_obb_main(interface, self._config_set, self._wall)
                else:
                    detail_obb = detail.get_detail_obb_cross(interface, self._config_set, self._wall)

                if detail_obb.contains_point(beam_def.centerline.midpoint):
                    self._beam_definitions.remove(beam_def)
                    break

    def distance_between_elements(self, element_one, element_two):
        distances = []
        for pt in element_one.centerline:
            cp = closest_point_on_segment(pt, element_two.centerline)
            distances.append(distance_point_point_sqrd(pt, cp))
        for pt in element_two.centerline:
            cp = closest_point_on_segment(pt, element_one.centerline)
            distances.append(distance_point_point_sqrd(pt, cp))
        return math.sqrt(min(distances))

    def generate_plates(self):
        plates = []
        if self._config_set.sheeting_inside:
            plates.append(Plate(self.outer_polyline.copy(), self._config_set.sheeting_inside))
        if self._config_set.sheeting_outside:
            pline = self.outer_polyline.copy()
            pline.translate(self.frame.zaxis * (self._wall.thickness + self._config_set.sheeting_outside))
            plates.append(Plate(pline, self._config_set.sheeting_outside))

        for opening in self._openings:
            for plate in plates:
                plate.add_feature(opening.boolean_feature)

        self._elements.extend(plates)


def shorten_edges_to_fit_between_plates(beams_to_fit, beams_to_fit_between, dist_tolerance=None):
    """Shorten the beams to fit between the plates. The given beam definitions are modified in-place.

    Parameters
    ----------
    beams_to_fit : list of :class:`BeamDefinition`
        The beams to fit between the plates.
    beams_to_fit_between : list of :class:`BeamDefinition`
        The plates to fit between.
    dist_tolerance : float, optional
        The distance tolerance for the intersection check.
        Default is ``TOL.absolute``.

    """
    plate_a, plate_b = beams_to_fit_between  # one is top, one is bottom, might be important to distinguish at some point.
    dist_tolerance = dist_tolerance or TOL.absolute
    for stud in beams_to_fit:
        start_point, _ = intersection_segment_segment(stud.centerline, plate_a.centerline, dist_tolerance)
        end_point, _ = intersection_segment_segment(stud.centerline, plate_b.centerline, dist_tolerance)
        if start_point and end_point:
            stud.centerline = Line(start_point, end_point)


def offset_elements(element_loop, edge_stud_offset=None, offset_inside=True):
    """Offset elements towards the inside of the wall. The given beam definitions are modified in-place.

    Parameters
    ----------
    element_loop : list of :class:`BeamDefinition`
        The elements to offset.
    edge_stud_offset : float, optional
        The additional offset for edge studs towards the inside of the wall to account for bending.
        Default is ``0.0``.
    offset_inside : bool, optional
        Offset the elements towards the inside of the wall.
        Default is ``True``. If ``False``, the elements are offset towards the outside.

    """
    # TODO: rename to offset_perimeter_elements
    edge_studs = [beam_def for beam_def in element_loop if beam_def.type in "edge_stud"]
    edge_stud_offset = edge_stud_offset or 0.0
    for beam_def in element_loop:
        # polyline is at the center of the beam's face, push it towards the inside
        beam_def.offset(beam_def.width / 2, reverse_dir=not offset_inside)

    for stud in edge_studs:
        # configurable additional offset for edge studs towards the inside of the wall to account for bending
        stud.offset(edge_stud_offset)
