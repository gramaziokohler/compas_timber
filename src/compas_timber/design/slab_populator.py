import math

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Projection
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import closest_point_on_plane
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import intersection_segment_segment
from compas.geometry import is_parallel_vector_vector
from compas.tolerance import TOL
from compas.itertools import pairwise

from compas_timber.design import JointRule
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication.longitudinal_cut import LongitudinalCutProxy
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import is_point_in_polyline

from .workflow import JointDefinition


class Window(object):
    """

    # TODO: is this an Element maybe?

    A window object for the SurfaceAssembly.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline` TODO; define with 2 polylines(inside and outside)
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
    stud_direction : :class:`compas.geometry.Vector`
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

    def __init__(self, outline, beam_dimensions, slab_frame, wall_thickness, stud_direction, tolerance, sheeting_inside=None, sheeting_outside=None, lintel_posts=None):
        self.beam_dimensions = beam_dimensions
        self._slab_frame = slab_frame
        self._sheeting_inside = sheeting_inside
        self._sheeting_outside = sheeting_outside
        self._lintel_posts = lintel_posts
        self._wall_thickness = wall_thickness
        self.outline = outline
        self.sill_height = self.beam_dimensions["sill"][0]
        self.header_height = self.beam_dimensions["header"][0]
        self.stud_direction = stud_direction
        self.normal = self._slab_frame.zaxis
        self._beams = []
        self._length = None
        self._height = None
        self._frame = None
        self.dist_tolerance = tolerance
        self.sill = None
        self.header = None
        self.joint_definitions = []

    @classmethod
    def from_outline_and_slab_populator(cls, slab_populator, outline):
        """Create a window in the slab and return it."""
        window = cls(
            outline,
            slab_populator.beam_dimensions,
            slab_populator.frame,
            slab_populator.frame_thickness,
            slab_populator.stud_direction,
            slab_populator.dist_tolerance,
            slab_populator.sheeting_inside,
            slab_populator.sheeting_outside,
            slab_populator.lintel_posts,
        )
        return window

    @property
    def obb(self):
        """Oriented bounding box of the window. used for creating framing elements around non-standard window shapes."""
        frame = Frame(self._slab_frame.point, cross_vectors(self.stud_direction, self.normal), self.stud_direction)
        rebase = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        box = Box.from_points(self.outline.transformed(rebase))
        rebase.invert()
        box.transform(rebase)
        return box

    @property
    def frame_polyline(self):
        return Polyline([self.obb.corner(0), self.obb.corner(1), self.obb.corner(2), self.obb.corner(3), self.obb.corner(0)])

    @property
    def studs(self):
        return [beam for beam in self._beams if beam.attributes["category"] == "jack_stud" or beam.attributes["category"] == "king_stud"]

    @property
    def jack_studs(self):
        return [beam for beam in self._beams if beam.attributes["category"] == "jack_stud"]

    @property
    def king_studs(self):
        return [beam for beam in self._beams if beam.attributes["category"] == "king_stud"]

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
        return self._frame

    def create_elements(self):
        segments = self.frame_polyline.lines
        self.header = beam_from_category(self, segments[1], "header", edge_index=1)
        left_king = beam_from_category(self, segments[2], "king_stud", edge_index=2)
        right_king = beam_from_category(self, segments[0], "king_stud", edge_index=0)
        self.sill = beam_from_category(self, segments[3], "sill", edge_index=3)
        self._beams = [self.header, self.sill, left_king, right_king]

        if self._lintel_posts:
            left_jack = beam_from_category(self, left_king.centerline, "jack_stud", edge_index=2, normal_offset=False)
            right_jack = beam_from_category(self, right_king.centerline, "jack_stud", edge_index=0, normal_offset=False)
            self._beams.extend([left_jack, right_jack])
            left_king.frame.translate(get_polyline_segment_perpendicular_vector(self.frame_polyline, 2) * self.beam_dimensions["jack_stud"][0])
            right_king.frame.translate(get_polyline_segment_perpendicular_vector(self.frame_polyline, 0) * self.beam_dimensions["jack_stud"][0])

        for beam in self._beams:
            vector = get_polyline_segment_perpendicular_vector(self.frame_polyline, beam.attributes["edge_index"])
            beam.frame.translate(vector * beam.width * 0.5)

        return self._beams

    def create_joint_definitions(self):
        self.joint_definitions.extend([JointDefinition(TButtJoint, [self.header, king])for king in self.king_studs])
        if self._lintel_posts:
            self.joint_definitions.extend([JointDefinition(TButtJoint, [self.sill, jack])for jack in self.jack_studs])
            self.joint_definitions.extend([JointDefinition(LButtJoint, [jack, self.header])for jack in self.jack_studs])
        else:
            self.joint_definitions.extend([JointDefinition(TButtJoint, [self.sill, king])for king in self.king_studs])

        return self.joint_definitions



class Door(Window):
    """TODO: revise when we know where this is going, maybe no need for classes here beyond Opening"""

    def __init__(self, outline, beam_dimensions, wall_frame, wall_thickness, tolerance, sheeting_inside=None, sheeting_outside=None, lintel_posts=None):
        super(Door, self).__init__(outline, beam_dimensions, wall_frame, wall_thickness, tolerance, sheeting_inside, sheeting_outside, lintel_posts)

    def create_elements(self):
        elements = super(Door, self).create_elements()
        return [e for e in elements if e.type != "sill"]


class SlabPopulatorConfigurationSet(object):
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
        stud_direction=None,
        tolerance=None,
        sheeting_outside=0,
        sheeting_inside=0,
        lintel_posts=True,
        edge_stud_offset=0.0,
        custom_dimensions=None,
        joint_overrides=None,
        wall_selector=None,
        connection_details=None,
    ):
        self.stud_spacing = stud_spacing
        self.beam_width = beam_width
        self.stud_direction = stud_direction
        self.tolerance = tolerance or TOL
        self.sheeting_outside = sheeting_outside
        self.sheeting_inside = sheeting_inside
        self.lintel_posts = lintel_posts
        self.edge_stud_offset = edge_stud_offset or 0.0
        self.custom_dimensions = custom_dimensions
        self.joint_overrides = joint_overrides
        self.wall_selector = wall_selector
        self.connection_details = connection_details or {}

    def __str__(self):
        return "SlabPopulatorConfigurationSet({}, {}, {})".format(self.stud_spacing, self.beam_width, self.stud_direction)

    @classmethod
    def default(cls, stud_spacing, beam_width):
        return cls(stud_spacing, beam_width)


class SlabPopulator(object):
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
        The length of the panel perpendicular to the z-axis.
    panel_height : float
        The height of the panel.
    frame : :class:`compas.geometry.Frame`
        The frame of the assembly.
    jack_studs : list of :class:`compas_timber.elements.Beam`
        The jack studs of the assembly.
    king_studs : list of :class:`compas_timber.elements.Beam`
        The king studs of the assembly.
    edge_studs : list of :class:`compas_timber.elements.Beam`
        The edge studs of the assembly.
    studs : list of :class:`compas_timber.elements.Beam`
        The studs of the assembly.
    sills : list of :class:`compas_timber.elements.Beam`
        The sills of the assembly.
    headers : list of :class:`compas_timber.elements.Beam`
        The headers of the assembly.
    plate_beams : list of :class:`compas_timber.elements.Beam`

    """

    BEAM_CATEGORY_NAMES = ["stud", "king_stud", "jack_stud", "edge_stud", "plate_beam", "header", "sill", "detail"]

    def __init__(self, configuration_set, slab, interfaces=None):
        self._slab = slab
        self._config_set = configuration_set
        if configuration_set.stud_direction:
            if is_parallel_vector_vector(slab.frame.normal, configuration_set.stud_direction):
                self.stud_direction = slab.frame.yaxis
            else:
                proj = Projection.from_plane(Plane.from_frame(slab.frame))
                self.stud_direction = configuration_set.stud_direction.transformed(proj)
        else:
            self.stud_direction = slab.frame.yaxis
        self.normal = slab.frame.zaxis  # out
        self.outline_a = slab.outline_a
        self.outline_b = slab.outline_b
        self.inner_polylines = slab.openings
        self.edges = []
        self._elements = []
        self._beams = []
        self._edge_beams = []
        self._plates = []
        self._rules = []
        self._features = []
        self.beam_dimensions = {}
        self.dist_tolerance = configuration_set.tolerance.relative
        self._edge_perpendicular_vectors = []

        self.frame = slab.frame
        self._interfaces = slab.interfaces or []
        self._adjusted_segments = {}
        self._plate_segments = {}
        self._detail_obbs = []
        self._openings = []
        self._joint_definitions = []
        self._interior_corner_indices = []
        self.frame_thickness = slab.thickness
        self.sheeting_inside = configuration_set.sheeting_inside or 0
        self.sheeting_outside = configuration_set.sheeting_outside or 0
        self.lintel_posts = configuration_set.lintel_posts
        if configuration_set.sheeting_inside:
            self.frame_thickness -= configuration_set.sheeting_inside
        if configuration_set.sheeting_outside:
            self.frame_thickness -= configuration_set.sheeting_outside

        for key in self.BEAM_CATEGORY_NAMES:
            self.beam_dimensions[key] = (configuration_set.beam_width, self.frame_thickness)
        if self._config_set.custom_dimensions:
            dimensions = self._config_set.custom_dimensions
            for key, value in dimensions.items():
                if value:
                    self.beam_dimensions[key] = value

        self.test_out = []

    def __repr__(self):
        return "SlabPopulator({}, {})".format(self._config_set, self._wall)

    @property
    def default_rules(self):
        edge_plate_joint = LButtJoint if TOL.is_zero(self._config_set.edge_stud_offset) else TButtJoint
        return [
            CategoryRule(edge_plate_joint, "edge_stud", "plate_beam"),
            CategoryRule(TButtJoint, "detail", "plate_beam"),  # TODO: have the details define this
            CategoryRule(LButtJoint, "detail_edge", "plate_beam"),  # TODO: have the details define this
            CategoryRule(TButtJoint, "stud", "plate_beam"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "stud", "sill"),
            CategoryRule(LButtJoint, "jack_stud", "plate_beam"),
            CategoryRule(TButtJoint, "jack_stud", "plate_beam"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "plate_beam"),
            CategoryRule(LButtJoint, "king_stud", "plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "sill", "jack_stud"),
            CategoryRule(TButtJoint, "stud", "detail"),
            CategoryRule(TButtJoint, "jack_stud", "detail"),
            CategoryRule(TButtJoint, "king_stud", "detail"),
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
    def elements(self):
        return self._beams + self._plates

    @property
    def features(self):
        return self._features

    @property
    def plate_elements(self):
        for plate in self._elements:
            if isinstance(plate, Plate):
                yield plate

    @property
    def edge_perpendicular_vectors(self):
        """Returns the perpendicular vectors for the edges of the slab."""
        if not self._edge_perpendicular_vectors:
            self._edge_perpendicular_vectors = [get_polyline_segment_perpendicular_vector(self.outline_a, i) for i in range(len(self.outline_a.lines))]
        return self._edge_perpendicular_vectors

    @property
    def points(self):
        return self.outer_polyline.points

    @property
    def jack_studs(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "jack_stud"]

    @property
    def king_studs(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "king_stud"]

    @property
    def edge_studs(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "edge_stud"]

    @property
    def studs(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "stud"]

    @property
    def sills(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "sill"]

    @property
    def headers(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "header"]

    @property
    def plate_beams(self):
        return [beam for beam in self._beams if beam.attributes.get("category", None) == "plate_beam"]

    @property
    def interior_corner_indices(self):
        """Get the indices of the interior corners of the slab outline."""
        if not self._interior_corner_indices:
            """Get the indices of the interior corners of the slab outline."""
            points = self.outline_a.points[0:-1]
            cw = is_polyline_clockwise(self.outline_a, self.normal)
            for i in range(len(points)):
                angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], self.normal, deg=True)
                if not (cw ^ (angle < 0)):
                    self._interior_corner_indices.append(i)
        return self._interior_corner_indices

    @property
    def interior_segment_indices(self):
        """Get the indices of the interior segments of the slab outline."""
        for i in range(len(self.outline_a.lines)):
            if i in self.interior_corner_indices and (i + 1) % len(self.outline_a.lines) in self.interior_corner_indices:
                yield i

    @property
    def edge_interfaces(self):
        """Get the edge interfaces of the slab."""
        interfaces = {}
        for interface in self._interfaces:
            if interface.edge_index is not None:
                interfaces[interface.edge_index] = interface
        return interfaces

    @property
    def face_interfaces(self):
        """Get the face interfaces of the slab."""
        return [i for i in self._interfaces if i.edge_index is None]

    @classmethod
    def beam_category_names(cls):
        return SlabPopulator.BEAM_CATEGORY_NAMES

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
        self.generate_edge_beams()
        self.generate_interface_beams()

        self.generate_edge_joint_definitions()

        self.generate_face_joint_definitions()

        self.generate_openings()
        self.extend_beams()
        self.generate_stud_beams()
        self.generate_plates()
        return self.elements

    # ==========================================================================
    # methods for edge beams
    # ==========================================================================

    def generate_edges(self):
        self.generate_edge_beams()

    def generate_edge_beams(self, min_width=None):
        """Get the edge beam definitions for the outer polyline of the slab."""
        if min_width is None:
            min_width = self._config_set.beam_width
        bounding_pline, edge_beam_widths = self.get_bounding_polyline_and_widths()
        for i, (seg, width) in enumerate(zip(bounding_pline.lines, edge_beam_widths)):
            beam = Beam.from_centerline(seg, width=width + min_width, height=self.frame_thickness, z_vector=self.normal)
            beam.attributes["edge_index"] = i
            self.set_edge_beams_category(beam)
            self.offset_edge_beam(beam)
            self.trim_edge_beam(beam)
            self._edge_beams.append(beam)
        self._beams.extend(self._edge_beams)

    def get_bounding_polyline_and_widths(self):
        edge_segs = []
        edge_beam_widths = []
        for i in range(len(self.outline_a.lines)):
            seg, width = self.get_outer_segment_and_offset(i)
            edge_segs.append(seg)
            edge_beam_widths.append(width)
        pts = []
        for i in range(len(edge_segs)):
            pts.append(intersection_line_line(edge_segs[i - 1], edge_segs[i])[0])
        pts.append(pts[0])  # close the loop
        return Polyline(pts), edge_beam_widths

    def get_outer_segment_and_offset(self, segment_index):
        vector = self.edge_perpendicular_vectors[segment_index]
        vector.unitize()
        seg_a = self.outline_a.lines[segment_index]
        seg_b = self.outline_b.lines[segment_index]
        pt = closest_point_on_segment(seg_a.point_at(0.5), seg_b)
        dot = dot_vectors(vector, Vector.from_start_end(seg_a.point_at(0.5), pt))
        if dot <= 0:  # seg_b is closer to the middle
            return seg_a, -dot
        else:  # seg_a is closer to the middle
            return seg_b.translated(-self.normal * self._slab.thickness), dot

    def set_edge_beams_category(self, beam):
        if beam.attributes["edge_index"] in self.interior_segment_indices:
            if angle_vectors(beam.centerline.direction, self.stud_direction, deg=True) < 45 or angle_vectors(beam.centerline.direction, self.stud_direction, deg=True) > 135:
                beam.attributes["category"] = "king_stud"
            else:
                beam.attributes["category"] = "header"
        else:
            if angle_vectors(beam.centerline.direction, self.stud_direction, deg=True) < 45 or angle_vectors(beam.centerline.direction, self.stud_direction, deg=True) > 135:
                beam.attributes["category"] = "edge_stud"
            else:
                beam.attributes["category"] = "plate_beam"

    def trim_edge_beam(self, beam):
        """Trim the edge beams to fit between the plate beams."""
        plane = self._slab.edge_planes[beam.attributes["edge_index"]]
        if not TOL.is_zero(dot_vectors(self.normal, plane.normal)):
            long_cut = LongitudinalCutProxy.from_plane_and_beam(self._slab.edge_planes[beam.attributes["edge_index"]], beam)
            beam.add_features(long_cut)

    def offset_edge_beam(self, beam):
        """Offset elements towards the inside of the wall. The given beam definitions are modified in-place.

        Parameters
        ----------
        element_loop : list of :class:`BeamDefinition`
            The elements to offset.

        """
        vector = -self.edge_perpendicular_vectors[beam.attributes["edge_index"]]
        beam.frame.translate(vector * beam.width * 0.5)
        beam.frame.translate(self.normal * beam.height * 0.5)

    def generate_interface_beams(self):
        """Generate the beams for the interface."""
        for interface in self._slab.interfaces:
            if interface.interface_role == "CROSS":
                if interface.topology == JointTopology.TOPO_T:
                    self.generate_t_cross_beams(interface)

                elif interface.topology == JointTopology.TOPO_L:
                    self.generate_l_cross_beams(interface)

            elif interface.interface_role == "MAIN":
                if interface.topology == JointTopology.TOPO_T or interface.topology == JointTopology.TOPO_L:
                    interface.beams.append(self._edge_beams[interface.edge_index])

            elif interface.interface_role == "NONE":
                if interface.topology == JointTopology.TOPO_L:
                    interface.beams.append(self._edge_beams[interface.edge_index])
            else:
                raise ValueError("either topology: {} or interface role: {} is invalid".format(interface.topology, interface.interface_role))

    def generate_t_cross_beams(self, interface):
        """Generate the beams for a T-cross interface."""
        edge = interface.polyline.lines[0]
        edge.translate(interface.frame.yaxis * interface.width * 0.5)
        flat_beam = Beam.from_centerline(edge, width=self.beam_dimensions["stud"][1], height=self.beam_dimensions["stud"][0], z_vector=self.normal)
        flat_beam.frame.translate(interface.frame.zaxis * flat_beam.height * 0.5)
        stud_edge_a = edge.translated(interface.frame.yaxis * (self.beam_dimensions["stud"][0] + self.beam_dimensions["stud"][1]) * 0.5)
        stud_edge_b = edge.translated(-interface.frame.yaxis * (self.beam_dimensions["stud"][0] + self.beam_dimensions["stud"][1]) * 0.5)
        beam_a = beam_from_category(self, stud_edge_a, "stud")
        beam_b = beam_from_category(self, stud_edge_b, "stud")

        interface.beams = [beam_a, flat_beam, beam_b]
        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        self._beams.extend([beam_a, flat_beam, beam_b])

    def generate_l_cross_beams(self, interface):
        """Generate the beams for a T-cross interface."""
        edge_beam = self._edge_beams[interface.edge_index]
        edge = edge_beam.centerline
        flat_line = edge.translated(interface.frame.yaxis * (edge_beam.width + self.beam_dimensions["stud"][1]) * 0.5)
        inner_line = flat_line.translated(interface.frame.yaxis * (self.beam_dimensions["stud"][0] + self.beam_dimensions["stud"][1]) * 0.5)
        flat_line.translate(interface.frame.zaxis * (self.beam_dimensions["stud"][0] - edge_beam.height) * 0.5)
        edge.translate(interface.frame.yaxis * self.beam_dimensions["stud"][1] * 0.5)
        flat_beam = Beam.from_centerline(flat_line, width=self.beam_dimensions["stud"][1], height=self.beam_dimensions["stud"][0], z_vector=self.normal)
        inner_beam = beam_from_category(self, inner_line, "stud", normal_offset=False)
        interface.beams = [edge_beam, flat_beam, inner_beam]
        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        self._beams.extend([flat_beam, inner_beam])

    # ==========================================================================
    # methods for beam joints
    # ==========================================================================

    def generate_edge_joint_definitions(self):
        for i in range(len(self._edge_beams)):
            if i == 0:
                edge_interface_a = self.edge_interfaces.get(len(self._edge_beams) - 1, None)
            else:
                edge_interface_a = self.edge_interfaces.get(i - 1, None)
            edge_interface_b = self.edge_interfaces.get(i, None)
            if edge_interface_a and len(edge_interface_a.beams) > 1 and edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is an interface, we use the interface to create the joint definition
                self.get_edge_interface_edge_interface_joint_definition(edge_interface_a, edge_interface_b)
            elif edge_interface_a and len(edge_interface_a.beams) > 1:
                # if there is only an interface on the previous edge, we use that to create the joint definition
                self.get_edge_interface_beam_joint_definition(edge_interface_a, self._edge_beams[i])
            elif edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is only an interface on the next edge, we use that to create the joint definition
                self.get_edge_interface_beam_joint_definition(edge_interface_b, self._edge_beams[i - 1])
            else:
                # if there is no interface, we create a joint definition between the two edge beams
                self.get_edge_beam_joint_definition(i)

    def get_edge_interface_edge_interface_joint_definition(self, interface_a, interface_b):
        edge_index = interface_b.edge_index
        interface_a_angle = angle_vectors(interface_a.frame.xaxis, self.stud_direction)
        interface_a_angle = min(interface_a_angle, math.pi - interface_a_angle)
        interface_b_angle = angle_vectors(interface_b.frame.xaxis, self.stud_direction)
        interface_b_angle = min(interface_b_angle, math.pi - interface_b_angle)

        if edge_index in self.interior_corner_indices:
            if interface_a_angle < interface_b_angle:
                plane = Plane(self._slab.edge_planes[edge_index].point, -self._slab.edge_planes[edge_index].normal)  # a: main, b: cross
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[0], interface_b.beams[0]], butt_plane=plane))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[1], interface_b.beams[0]], butt_plane=plane))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[0], interface_a.beams[2]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[1], interface_a.beams[2]]))
                self._joint_definitions.append(JointDefinition(LButtJoint, [interface_b.beams[2], interface_a.beams[2]]))
            else:
                plane = Plane(self._slab.edge_planes[edge_index - 1].point, -self._slab.edge_planes[edge_index - 1].normal)  # b: main, a: cross
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[0], interface_a.beams[0]], butt_plane=plane))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[1], interface_a.beams[0]], butt_plane=plane))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[0], interface_b.beams[2]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[1], interface_b.beams[2]]))
                self._joint_definitions.append(JointDefinition(LButtJoint, [interface_a.beams[2], interface_b.beams[2]]))
        else:
            if interface_a_angle < interface_b_angle:
                self._joint_definitions.append(JointDefinition(LButtJoint, [interface_b.beams[0], interface_a.beams[0]], back_plane=self._slab.edge_planes[edge_index]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[1], interface_a.beams[0]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[2], interface_a.beams[0]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[1], interface_b.beams[2]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[2], interface_b.beams[2]]))

            else:
                self._joint_definitions.append(JointDefinition(LButtJoint, [interface_a.beams[0], interface_b.beams[0]], back_plane=self._slab.edge_planes[edge_index - 1]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[1], interface_b.beams[0]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_a.beams[2], interface_b.beams[0]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[1], interface_a.beams[2]]))
                self._joint_definitions.append(JointDefinition(TButtJoint, [interface_b.beams[2], interface_a.beams[2]]))

    def get_edge_interface_beam_joint_definition(self, interface, beam):
        beam_index = beam.attributes["edge_index"]
        interface_index = interface.edge_index
        corner_index = max(interface_index, beam_index)

        if corner_index in self.interior_corner_indices:
            plane = Plane(self._slab.edge_planes[beam_index].point, -self._slab.edge_planes[beam_index].normal)
            self._joint_definitions.append(JointDefinition(TButtJoint, [interface.beams[0], beam], butt_plane=plane))
            self._joint_definitions.append(JointDefinition(TButtJoint, [interface.beams[1], beam], butt_plane=plane))
            self._joint_definitions.append(JointDefinition(LButtJoint, [interface.beams[2], beam], butt_plane=plane))
        else:
            plane = Plane(self._slab.edge_planes[interface_index].point, -self._slab.edge_planes[interface_index].normal)
            self._joint_definitions.append(JointDefinition(LButtJoint, [interface.beams[0], beam], back_plane=self._slab.edge_planes[interface_index]))
            self._joint_definitions.append(JointDefinition(TButtJoint, [interface.beams[1], beam]))
            self._joint_definitions.append(JointDefinition(TButtJoint, [interface.beams[2], beam]))

    def get_edge_beam_joint_definition(self, edge_index):
        beam_a = self._edge_beams[edge_index - 1]
        beam_b = self._edge_beams[edge_index]
        beam_a_angle = angle_vectors(beam_a.centerline.direction, self.stud_direction)
        beam_a_angle = min(beam_a_angle, math.pi - beam_a_angle)  # get the smallest angle to the stud direction
        beam_b_angle = angle_vectors(beam_b.centerline.direction, self.stud_direction)
        beam_b_angle = min(beam_b_angle, math.pi - beam_b_angle)  # get the smallest angle to the stud direction

        if edge_index in self.interior_corner_indices:
            if beam_a_angle < beam_b_angle:
                plane = Plane(self._slab.edge_planes[edge_index].point, -self._slab.edge_planes[edge_index].normal)
                joint_def = JointDefinition(LButtJoint, [beam_a, beam_b], butt_plane=plane)
            else:
                plane = Plane(self._slab.edge_planes[edge_index - 1].point, -self._slab.edge_planes[edge_index - 1].normal)
                joint_def = JointDefinition(LButtJoint, [beam_b, beam_a], butt_plane=plane)
        else:
            if beam_a_angle < beam_b_angle:
                joint_def = JointDefinition(LButtJoint, [beam_a, beam_b], back_plane=self._slab.edge_planes[edge_index - 1])
            else:
                joint_def = JointDefinition(LButtJoint, [beam_b, beam_a], back_plane=self._slab.edge_planes[edge_index])
        self._joint_definitions.append(joint_def)

    def generate_face_joint_definitions(self):
        """Generate the joint definitions for the face interfaces."""
        for interface in self.face_interfaces:
            for beam in interface.beams:
                pts = {}
                for i, seg in enumerate(self.outline_a.lines):
                    pt = intersection_line_segment(beam.centerline, seg)[0]
                    if pt:
                        pts[i] = pt
                if len(pts.values()) != 2:
                    raise ValueError("Could not find intersection points between beam {} and outline segments: {}".format(beam, pts))
                else:
                    for i in pts.keys():
                        if self.edge_interfaces.get(i, None) and len(self.edge_interfaces[i].beams) > 0:
                            # if there is an interface with beams, we use the last interface beam to create the joint definition
                            self._joint_definitions.append(JointDefinition(TButtJoint, [beam, self.edge_interfaces[i].beams[-1]]))
                        else:
                            # if there is no interface, we create a joint definition between the edge beam and the beam
                            self._joint_definitions.append(JointDefinition(TButtJoint, [beam, self._edge_beams[i]]))

    # ==========================================================================
    # methods for stud beams
    # ==========================================================================


    def generate_openings(self):
        for opening in self.inner_polylines:
            element = Window.from_outline_and_slab_populator(self, opening)
            self._openings.append(element)
            self._beams.extend(element.create_elements())
            self._joint_definitions.extend(element.create_joint_definitions())

    def extend_beams(self):
        for joint in self._joint_definitions



    def generate_stud_beams(self):
        self.generate_studs()
        self.join_studs()
        self.join_jack_studs()
        self.join_king_studs()
        self.cull_overlaps()


    def get_stud_lines(self):
        stud_lines = []
        x_position = self._config_set.stud_spacing
        frame = Frame(self._slab.frame.point, cross_vectors(self.stud_direction, self.normal), self.stud_direction)
        to_world = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        pts = [pt.transformed(to_world) for pt in self.outline_a.points + self.outline_b.points]
        box = Box.from_points(pts)
        x_position = box.xmin + self._config_set.stud_spacing
        to_local = Transformation.from_frame_to_frame(Frame.worldXY(), frame)
        while x_position < box.xmax - self.beam_dimensions["stud"][0]:
            start_point = Point(x_position, 0, 0)
            start_point.transform(to_local)
            stud_lines.append(Line.from_point_and_vector(start_point, self.stud_direction))
            x_position += self._config_set.stud_spacing
        return stud_lines



    def generate_studs(self):
        stud_lines = self.get_stud_lines()
        for line in stud_lines:
            intersections = []
            #get intersections with outline
            for i, segment in enumerate(self.outline_a.lines):
                point = intersection_line_segment(line, segment)[0]
                if point:
                    print("intersection with outline segment {}: {}".format(i, point))
                    intersection = {}
                    intersection["point"] = point
                    intersection["dot"] = dot_vectors(Vector.from_start_end(line.point_at(0.5), point), self.stud_direction)
                    intersection["edge_index"] = i
                    intersections.append(intersection)
            #get intersections with openings
            for opening in self._openings:
                for beam in [opening.sill, opening.header]:
                    point = intersection_line_segment(line, beam.centerline)[0]
                    if point:
                        intersection = {}
                        intersection["point"] = point
                        intersection["dot"] = dot_vectors(Vector.from_start_end(line.point_at(0.5), point), self.stud_direction)
                        intersection["beam"] = beam
                        intersections.append(intersection)
            #get intersections with interfaces
            for interface in self._slab.interfaces:
                if interface.interface_role == "CROSS":
                    for segment in interface.polyline.lines:
                        point = intersection_line_segment(line, segment)[0]
                        if point:
                            intersection = {}
                            intersection["point"] = point
                            intersection["dot"] = dot_vectors(Vector.from_start_end(line.point_at(0.5), point), self.stud_direction)
                            intersection["edge_index"] = interface.edge_index
                            intersections.append(intersection)
            intersections.sort(key=lambda x: x["dot"])

            for pair in pairwise(intersections):
                make_beam = True
                line = Line(pair[0]["point"], pair[1]["point"])
                if TOL.is_zero(line.length):
                    make_beam = False
                if not is_point_in_polyline(line.point_at(0.5), self.outline_a):

                    make_beam = False
                for i in self._slab.interfaces:
                    if is_point_in_polyline(line.point_at(0.5), i.polyline):
                        make_beam = False
                for o in self._openings:
                    if is_point_in_polyline(line.point_at(0.5), o.frame_polyline):
                        make_beam = False
                if make_beam:
                    stud_segment = beam_from_category(self, line, "stud")
                    for intersection in pair:
                        beam = intersection.get("beam", None)
                        if beam:
                            self.test_out.append(beam.blank)
                            self._joint_definitions.append(JointDefinition(TButtJoint, [stud_segment, beam]))
                            break
                        edge_index = intersection.get("edge_index", None)
                        print("edge_index", edge_index)
                        if edge_index is not None:
                            interface = self.edge_interfaces.get(edge_index, None)
                            if interface:
                                print("interface found for edge index {}: {}".format(edge_index, interface))
                                print("interface beams = {}".format(interface.beams))
                                self._joint_definitions.append(JointDefinition(TButtJoint, [stud_segment, interface.beams[-1]]))
                                break
                            else:
                                print("edge_beam_no_interface", self._edge_beams[edge_index])
                                self._joint_definitions.append(JointDefinition(TButtJoint, [stud_segment, self._edge_beams[edge_index]]))
                                break
                    self._beams.append(stud_segment)



            # if len(intersections) == 0 or len(intersections) % 2 != 0:
            #     raise ValueError("The number of intersection points between the stud line and the outline segments is not even: {}".format(intersections))
            # if len(intersections)% 2 == 0:
            #     intersections.sort(key=lambda x: x["dot"])
            #     int_pts = [x["point"] for x in intersections]
            #     beams = [x["beam"] for x in intersections]
            #     while len(int_pts)>=2:
            #         start = int_pts.pop()
            #         start_beam = beams.pop()
            #         end = int_pts.pop()
            #         end_beam = beams.pop()
            #         new_line = Line(start, end)

            #         stud_segment = beam_from_category(self, new_line, "stud")
            #         self._beams.append(stud_segment)


    def join_studs(self):
        rules = [
            CategoryRule(TButtJoint, "stud", "plate_beam"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "stud", "sill"),
            CategoryRule(TButtJoint, "stud", "detail"),
            CategoryRule(TButtJoint, "stud", "edge_stud"),
        ]
        stud_joint_defs = JointRule.joints_from_beams_and_rules(self._beams, rules, handled_pairs = [jdef.elements for jdef in self._joint_definitions])[0]
        print([[jdef.joint_type, jdef.elements[0].attributes["category"],jdef.elements[1].attributes["category"]] for jdef in stud_joint_defs])
        self._joint_definitions.extend(stud_joint_defs)

    def join_jack_studs(self):
        for jack_stud in self.jack_studs:
            intersections = []

            for i, segment in enumerate(self.outline_a.lines):
                point = intersection_line_segment(jack_stud.centerline,segment)[0]
                if point:
                    intersection = {}
                    intersection["dot"] = dot_vectors(Vector.from_start_end(jack_stud.centerline.point_at(0.5), point), self.stud_direction)
                    if self.edge_interfaces.get(i, None):
                        intersection["beam"] = self.edge_interfaces[i].beams[-1]
                    else:
                        intersection["beam"] = self._edge_beams[i]
                    print("Jack stud intersection with edge beam: {}".format(intersection))
                    intersections.append(intersection)
            for opening in self._openings:
                point = intersection_line_segment(jack_stud.centerline,opening.header.centerline)[0]
                if point:
                    intersection = {}
                    intersection["dot"] = dot_vectors(Vector.from_start_end(jack_stud.centerline.point_at(0.5), point), self.stud_direction)
                    intersection["beam"] = opening.header
                    intersections.append(intersection)
            negatives = [x for x in intersections if x["dot"] < 0]
            negatives.sort(key=lambda x: x["dot"])
            beam = negatives[-1]["beam"]
            self._joint_definitions.append(JointDefinition(TButtJoint, [jack_stud, beam]))


    def join_king_studs(self):
        for king_stud in self.king_studs:
            intersections = []
            for i, segment in enumerate(self.outline_a.lines):
                point = intersection_line_segment(king_stud.centerline,segment)[0]
                if point:
                    intersection = {}
                    intersection["dot"] = dot_vectors(Vector.from_start_end(king_stud.centerline.point_at(0.5), point), self.stud_direction)
                    if self.edge_interfaces.get(i, None):
                        intersection["beam"] = self.edge_interfaces[i].beams[-1]
                    else:
                        intersection["beam"] = self._edge_beams[i]
                    intersections.append(intersection)
            for opening in self._openings:
                point = intersection_line_segment(king_stud.centerline,opening.header.centerline)[0]
                if point:
                    intersection = {}
                    intersection["dot"] = dot_vectors(Vector.from_start_end(king_stud.centerline.point_at(0.5), point), self.stud_direction)
                    intersection["beam"] = opening.header
                    intersections.append(intersection)
            negatives = [x for x in intersections if x["dot"] < 0]
            negatives.sort(key=lambda x: x["dot"])
            bottom_beam = negatives[-1]["beam"]
            self._joint_definitions.append(JointDefinition(TButtJoint, [king_stud, bottom_beam]))
            positives = [x for x in intersections if x["dot"] > 0]
            positives.sort(key=lambda x: x["dot"])
            top_beam = positives[0]["beam"]
            self._joint_definitions.append(JointDefinition(TButtJoint, [king_stud, top_beam]))


    def cull_overlaps(self):
        not_studs = [beam for beam in self._beams if beam.attributes.get("category", None) is not "stud"]
        for stud in self.studs:
            for other_element in not_studs:
                if (
                    self.distance_between_elements(stud, other_element)
                    < (self.beam_dimensions[stud.attributes["category"]][0] + self.beam_dimensions[other_element.attributes["category"]][0]) / 2
                ):
                    self._beams.remove(stud)
                    break

    def distance_between_elements(self, element_one, element_two):
        pt = element_one.centerline.point_at(0.5)
        cp = closest_point_on_segment(pt, element_two.centerline)
        return pt.distance_to_point(cp)

    def generate_plates(self):
        plates = []
        if self._config_set.sheeting_inside:
            plate = Plate.from_outline_thickness(self.outer_polyline, self._config_set.sheeting_inside, self.normal)
            plates.append(plate)
        if self._config_set.sheeting_outside:
            pline = self.outer_polyline.translated(self.frame.zaxis * (self._wall.thickness - self._config_set.sheeting_outside))
            plate = Plate.from_outline_thickness(pline, self._config_set.sheeting_outside, self.normal)
            plates.append(plate)
        for plate in plates:
            for opening in self._openings:
                projected_outline = Polyline([closest_point_on_plane(pt, Plane.from_frame(plate.frame)) for pt in opening.outline])
                plate.add_feature(FreeContour.from_polyline_and_element(projected_outline, plate, interior=True))
        self._elements.extend(plates)

def shorten_edges_to_fit_between_plate_beams(beams_to_fit, beams_to_fit_between, dist_tolerance=None):
    """Shorten the beams to fit between the plate_beams. The given beam definitions are modified in-place.

    Parameters
    ----------
    beams_to_fit : list of :class:`BeamDefinition`
        The beams to fit between the plate_beams.
    beams_to_fit_between : list of :class:`BeamDefinition`
        The plate_beams to fit between.
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


def beam_from_category(parent, segment, category, normal_offset=True, **kwargs):
    width = parent.beam_dimensions[category][0]
    height = parent.beam_dimensions[category][1]
    beam = Beam.from_centerline(segment, width=width, height=height, z_vector=parent.normal)
    if normal_offset:
        beam.frame.translate(parent.normal * height * 0.5)  # align the beam to the slab frame
    beam.attributes["category"] = category
    for key, value in kwargs.items():
        beam.attributes[key] = value
    return beam

def distance_segment_segment(segment_a, segment_b):
    pts = []
    for intersection, segment in zip(intersection_line_line(segment_a,segment_b), [segment_a, segment_b]):
        if intersection is None:
            return None
        dot = dot_vectors(Vector.from_start_end(segment.start, segment.end), Vector.from_start_end(segment.start, intersection))/segment.length
        if dot>1:
            pts.append(segment.end)
        elif dot<0:
            pts.append(segment.start)
        else:
            pts.append(intersection)
    return pts[0].distance_to_point(pts[1])
