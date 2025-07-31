import math
import itertools

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Projection
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import closest_point_on_line
from compas.geometry import closest_point_on_plane
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import distance_point_point_sqrd
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import intersection_segment_segment
from compas.geometry import intersection_segment_polyline
from compas.geometry import is_parallel_vector_vector
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication.longitudinal_cut import LongitudinalCutProxy
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import distance_segment_segment
from compas_timber.utils import distance_segment_segment_points
from compas_timber.utils import get_segment_overlap


class SlabSelector(object):
    """Selects slabs based on their attributes."""

    def __init__(self, slab_attr, attr_value):
        self._slab_attr = slab_attr
        self._attr_value = attr_value

    def select(self, slab):
        value = getattr(slab, self._slab_attr, None)
        if value is None:
            return False
        else:
            return value == self._attr_value


class AnySlabSelector(object):
    def select(self, _):
        return True


class Window(object):
    """

    # TODO: is this an Element maybe?

    A window object for the SurfaceAssembly.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline` TODO: define with 2 polylines(inside and outside)
        The outline of the window.
    parent : :class:`compas_timber.model.SurfaceAssembly`
        The parent of the window.

    Attributes
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the window.
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

    # TODO: consider make opening generate an interface. it shares a lot of characteristics, e.g. it adds beams, joints, etc.

    def __init__(self, outline, slab_populator, lintel_posts=None):
        self.outline = outline
        self.slab_populator = slab_populator
        self._lintel_posts = lintel_posts or slab_populator._config_set.lintel_posts
        self.beams = []
        self.joints = []
        self.sill = None
        self.header = None
        self._frame = None

    @property
    def default_rules(self):
        return [
            CategoryRule(TButtJoint, "header", "king_stud"),
            CategoryRule(TButtJoint, "sill", "king_stud"),
            CategoryRule(TButtJoint, "sill", "jack_stud"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
        ]

    @property
    def wall_thickness(self):
        """The wall thickness of the slab."""
        return self.slab_populator.frame_thickness

    @property
    def stud_direction(self):
        """The stud direction of the slab."""
        return self.slab_populator.stud_direction

    @property
    def frame(self):
        """Frame of the window, aligned with the slab frame."""
        if self._frame is None:
            self._frame = Frame(self.outline[0], cross_vectors(self.stud_direction, self.normal), self.stud_direction)
        return self._frame

    @property
    def normal(self):
        return self.slab_populator.normal

    @property
    def tolerance(self):
        """The tolerance of the slab populator."""
        return self.slab_populator.dist_tolerance

    @property
    def beam_dimensions(self):
        """Beam dimensions of the window, based on the slab populator."""
        return self.slab_populator.beam_dimensions

    @property
    def obb(self):
        """Oriented bounding box of the window. used for creating framing elements around non-standard window shapes."""
        rebase = Transformation.from_frame_to_frame(self.frame, Frame.worldXY())
        box = Box.from_points(self.outline.transformed(rebase))
        rebase.invert()
        box.transform(rebase)
        return box

    @property
    def frame_polyline(self):
        """Bounding rectangle aligned orthogonal to the slab.stud_direction."""
        return Polyline([self.obb.corner(0), self.obb.corner(1), self.obb.corner(2), self.obb.corner(3), self.obb.corner(0)])

    @property
    def studs(self):
        return [beam for beam in self.beams if beam.attributes["category"] == "jack_stud" or beam.attributes["category"] == "king_stud"]

    @property
    def jack_studs(self):
        return [beam for beam in self.beams if beam.attributes["category"] == "jack_stud"]

    @property
    def king_studs(self):
        return [beam for beam in self.beams if beam.attributes["category"] == "king_stud"]

    def create_elements(self):
        segments = [l for l in self.frame_polyline.lines]
        for i in range(4):
            if dot_vectors(segments[i].direction, self.slab_populator.stud_direction) < 0:
                segments[i] = Line(segments[i].end, segments[i].start)  # reverse the segment to match the stud direction
        self.header = beam_from_category(self, segments[1], "header", edge_index=1)
        left_king = beam_from_category(self, segments[2], "king_stud", edge_index=2)
        right_king = beam_from_category(self, segments[0], "king_stud", edge_index=0)
        self.sill = beam_from_category(self, segments[3], "sill", edge_index=3)
        self.beams = [self.header, self.sill, left_king, right_king]

        for beam in self.beams:
            vector = get_polyline_segment_perpendicular_vector(self.frame_polyline, beam.attributes["edge_index"])
            beam.frame.translate(vector * beam.width * 0.5)

        if self._lintel_posts:
            left_jack = beam_from_category(self, left_king.centerline, "jack_stud", edge_index=2, normal_offset=False)
            right_jack = beam_from_category(self, right_king.centerline, "jack_stud", edge_index=0, normal_offset=False)
            self.beams.extend([left_jack, right_jack])
            left_king.frame.translate(get_polyline_segment_perpendicular_vector(self.frame_polyline, 2) * (self.beam_dimensions["jack_stud"][0]+self.beam_dimensions["king_stud"][0])*0.5)
            right_king.frame.translate(get_polyline_segment_perpendicular_vector(self.frame_polyline, 0) * (self.beam_dimensions["jack_stud"][0]+self.beam_dimensions["king_stud"][0])*0.5)


        return self.beams

    def create_joints(self):
        self.joints.extend([self.slab_populator.get_joint_from_elements(self.header, king, self.default_rules) for king in self.king_studs])
        if self._lintel_posts:
            self.joints.extend([self.slab_populator.get_joint_from_elements(self.sill, jack, self.default_rules) for jack in self.jack_studs])
            self.joints.extend([self.slab_populator.get_joint_from_elements(jack, self.header, self.default_rules) for jack in self.jack_studs])
        else:
            self.joints.extend([self.slab_populator.get_joint_from_elements(self.sill, king, self.default_rules) for king in self.king_studs])
        self._join_jack_studs()
        self._join_king_studs()
        return self.joints

    def _join_jack_studs(self):
        for jack_stud in self.jack_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in self.slab_populator._edge_beams.values():
                beams.extend(val)
            for opening in self.slab_populator._openings:
                if opening != self:
                    beams.extend([opening.header])
            # get intersections
            intersections = intersection_line_beams(jack_stud.centerline, beams, max_distance=self.beam_dimensions["jack_stud"][0])
            if not intersections:
                continue
            #get closest intersection to the bottom of the jack stud
            intersections.sort(key=lambda x: x["dot"])
            bottom_int = None
            for intersection in intersections:
                if intersection["dot"] < 0:
                    bottom_int = intersection
                else:
                    break
            #create joint
            self.joints.append(self.slab_populator.get_joint_from_elements(jack_stud, bottom_int["beam"], rules=self.default_rules))

    def _join_king_studs(self):
        for king_stud in self.king_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in self.slab_populator._edge_beams.values():
                beams.extend(val)
            for opening in self.slab_populator._openings:
                if opening != self:
                    beams.extend([opening.sill, opening.header])

            # get intersections
            intersections = intersection_line_beams(king_stud.centerline, beams, max_distance=self.beam_dimensions["king_stud"][0])
            if not intersections:
                continue

            # get closest intersections to the top and bottom of the king stud
            intersections.sort(key=lambda x: x["dot"])
            bottom_int = None
            top_int = None
            for intersection in intersections:
                if intersection["dot"] < 0:
                    bottom_int = intersection
                else:
                    top_int = intersection
                    break
            #create joints
            self.joints.append(self.slab_populator.get_joint_from_elements(king_stud, bottom_int["beam"], rules=self.default_rules))
            self.joints.append(self.slab_populator.get_joint_from_elements(king_stud, top_int["beam"], rules=self.default_rules))




class Door(Window):
    """TODO: revise when we know where this is going, maybe no need for classes here beyond Opening"""

    def __init__(self, outline, slab_populator, split_bottom_plate=True, lintel_posts=None):
        super(Door, self).__init__(outline, slab_populator, lintel_posts)
        self.split_bottom_plate = split_bottom_plate
        self.bottom_plate_beams = []

    @property
    def default_rules(self):
        rules = super(Door, self).default_rules
        if self.split_bottom_plate:
            if self._lintel_posts:
                for rule in rules:
                    if rule.category_a == "jack_stud" and rule.category_b == "bottom_plate_beam":
                        rules.remove(rule)
                rules.append(CategoryRule(LButtJoint, "jack_stud", "bottom_plate_beam"))
            else:
                for rule in rules:
                    if rule.category_a == "king_stud" and rule.category_b == "bottom_plate_beam":
                        rules.remove(rule)
                rules.append(CategoryRule(LButtJoint, "king_stud", "bottom_plate_beam"))
        return rules

    @property
    def jamb_studs(self):
        if self._lintel_posts:
            return self.jack_studs
        return self.king_studs


    def _comply_with_slab(self):
        segments = self.frame_polyline.lines[0:3]
        for door_frame_seg, edge_stud in itertools.product(segments, self.slab_populator.edge_studs):
            if distance_segment_segment(door_frame_seg, edge_stud.centerline) < edge_stud.width * 0.5 + self.beam_dimensions["king_stud"][0]:
                raise ValueError("door is too close to the slab edge {}".format(edge_stud.attributes["edge_index"]))


    def create_elements(self):
        self.beams = super(Door, self).create_elements()
        self.beams.remove(self.sill)
        if self.split_bottom_plate:
            for beam in self.slab_populator.bottom_plate_beams:
                overlap = get_segment_overlap(beam.centerline, self.sill.centerline)

                if overlap[0] is None:
                    continue
                if not (overlap[0]>0 and overlap[1]<beam.length):
                    continue

                new_beam = beam.copy()
                new_beam.attributes.update(beam.attributes)
                new_beam.length = beam.length - overlap[1]
                beam.length = overlap[0]
                new_beam.frame.translate(beam.frame.xaxis * overlap[1])

                self.bottom_plate_beams = [beam, new_beam]
                self.slab_populator._edge_beams[beam.attributes["edge_index"]].append(new_beam)
                break

        return self.beams


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

    BEAM_CATEGORY_NAMES = ["stud", "king_stud", "jack_stud", "edge_stud", "top_plate_beam", "bottom_plate_beam", "header", "sill", "detail"]

    def __init__(self, configuration_set, slab):
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
        self._edge_beams = {}
        self.plates = []
        self.studs = []
        self._rules = []
        self.beam_dimensions = {}
        self.dist_tolerance = configuration_set.tolerance.relative
        self._edge_perpendicular_vectors = []

        self.frame = slab.frame
        self._interfaces = slab.interfaces or []
        self._adjusted_segments = {}
        self._plate_segments = {}
        self._detail_obbs = []
        self._openings = []
        self._joints = []
        self._interior_corner_indices = []
        self.frame_thickness = slab.thickness
        self.sheeting_inside = configuration_set.sheeting_inside or 0
        self.sheeting_outside = configuration_set.sheeting_outside or 0
        self.lintel_posts = configuration_set.lintel_posts


        if configuration_set.sheeting_inside:
            offset_inside = configuration_set.sheeting_inside/slab.thickness
            pts_inside = []
            for pt_a, pt_b in zip(self.outline_a.points, self.outline_b.points):
                pt = pt_a * (1 - offset_inside) + pt_b * offset_inside
                pts_inside.append(pt)
            self.frame_thickness -= configuration_set.sheeting_inside
            self.frame_outline_a = Polyline(pts_inside)
        else:
            self.frame_outline_a = self.outline_a
        if configuration_set.sheeting_outside:
            offset_outside = configuration_set.sheeting_outside/slab.thickness
            pts_outside = []
            for pt_a, pt_b in zip(self.outline_a.points, self.outline_b.points):
                pts_outside.append(pt_a * offset_outside + pt_b * (1-offset_outside))
            self.frame_thickness -= configuration_set.sheeting_outside
            self.frame_outline_b = Polyline(pts_outside)
        else:
            self.frame_outline_b = self.outline_b

        for key in self.BEAM_CATEGORY_NAMES:
            self.beam_dimensions[key] = (configuration_set.beam_width, self.frame_thickness)
        if self._config_set.custom_dimensions:
            dimensions = self._config_set.custom_dimensions
            for key, value in dimensions.items():
                if value:
                    self.beam_dimensions[key] = (value[0], self.frame_thickness)
        self.test_out = []  # DEBUG used for debugging, to see if the slab is correctly populated

    def __repr__(self):
        return "SlabPopulator({}, {})".format(self._config_set, self._wall)

    @property
    def elements(self):
        return self.beams + self.plates

    @property
    def beams(self):
        beams = []
        for val in self._edge_beams.values():
            beams.extend(val)
        for interface in self._interfaces:
            beams.extend(interface.beams)
        for opening in self._openings:
            beams.extend(opening.beams)
        beams.extend(self.studs)
        return list(set(beams))

    @property
    def edge_perpendicular_vectors(self):
        """Returns the perpendicular vectors for the edges of the slab."""
        if not self._edge_perpendicular_vectors:
            self._edge_perpendicular_vectors = [get_polyline_segment_perpendicular_vector(self.outline_a, i) for i in range(len(self.outline_a.lines))]
        return self._edge_perpendicular_vectors

    @property
    def jack_studs(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "jack_stud"]

    @property
    def king_studs(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "king_stud"]

    @property
    def edge_studs(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "edge_stud"]


    @property
    def sills(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "sill"]

    @property
    def headers(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "header"]

    @property
    def top_plate_beams(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "top_plate_beam"]

    @property
    def bottom_plate_beams(self):
        return [beam for beam in self.beams if beam.attributes.get("category", None) == "bottom_plate_beam"]

    @property
    def plate_beams(self):
        return self.top_plate_beams + self.bottom_plate_beams

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
    def default_rules(self):
        return [
            CategoryRule(TButtJoint, "stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "jack_stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
            CategoryRule(LButtJoint, "edge_stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
            CategoryRule(LButtJoint, "edge_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "stud", "sill"),
            CategoryRule(TButtJoint, "stud", "edge_stud"),
            CategoryRule(LButtJoint, "king_stud", "edge_stud"),
            CategoryRule(LButtJoint, "jack_stud", "edge_stud"),
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
        slabs = list(model.slabs)  # TODO: these are anoying, consider making these lists again
        if len(slabs) != len(configuration_sets):
            raise ValueError("Number of walls and configuration sets do not match")

        slab_populators = []
        for slab in slabs:
            for config_set in configuration_sets:
                if config_set.slab_selector.select(slab):
                    interfaces = [interaction.get_interface_for_slab(slab) for interaction in model.get_interactions_for_element(slab)]
                    slab_populators.append(cls(config_set, slab, interfaces))
                    break
        return slab_populators

    def create_elements(self):
        """Does the actual populating of the wall
        creates and returns all the elements in the wall, returns also the joint definitions
        """
        self._generate_edge_beams()
        self._generate_interface_beams()
        self._extend_interface_beams()
        self._generate_openings()
        self._generate_stud_beams()
        self._generate_plates()
        self._generate_edge_joints()
        self._generate_face_joints()
        self._generate_opening_joints()
        self._cull_overlaps()
        return self.elements


    def generate_joints(self):
        self._generate_edge_joints()
        self._generate_face_joints()
        self._generate_opening_joints()
        self._cull_overlaps()


    def get_joint_from_elements(self, element_a, element_b, rules=None, **kwargs):
        """Get the joint type for the given elements."""
        if rules is None:
            rules = self.rules
        for rule in rules:
            if rule.category_a == element_a.attributes["category"] and rule.category_b == element_b.attributes["category"]:
                rule.kwargs.update(kwargs)
                return rule.joint_type(element_a, element_b, **rule.kwargs)
        raise ValueError("No joint definition found for {} and {}".format(element_a.attributes["category"], element_b.attributes["category"]))

    # ==========================================================================
    # methods for edge beams
    # ==========================================================================

    def _generate_edge_beams(self, min_width=None):
        """Get the edge beam definitions for the outer polyline of the slab."""
        if min_width is None:
            min_width = self._config_set.beam_width
        edge_segs, edge_beam_widths = self._get_edge_segments_and_widths()
        for i, (seg, width) in enumerate(zip(edge_segs, edge_beam_widths)):
            beam = Beam.from_centerline(seg, width=width + min_width, height=self.frame_thickness, z_vector=self.normal)
            beam.attributes["edge_index"] = i
            self._set_edge_beams_category(beam)
            self._offset_edge_beam(beam)
            self._apply_linear_cut_to_edge_beam(beam)
            self._edge_beams[i] = [beam]

    def _get_edge_segments_and_widths(self):
        edge_segs = []
        edge_beam_widths = []
        for i in range(len(self.outline_a.lines)):
            seg, width = self._get_outer_segment_and_offset(i)
            edge_segs.append(seg)
            edge_beam_widths.append(width)
        return edge_segs, edge_beam_widths

    def _get_outer_segment_and_offset(self, segment_index):
        vector = self.edge_perpendicular_vectors[segment_index]
        seg_a = self.frame_outline_a.lines[segment_index]
        seg_b = self.frame_outline_b.lines[segment_index]
        dot = dot_vectors(vector, Vector.from_start_end(seg_a.start, seg_b.start))
        if dot <= 0:  # seg_b is closer to the middle
            return seg_a, -dot
        else:  # seg_a is closer to the middle
            return seg_b.translated(-self.normal * self.frame_thickness), dot

    def _set_edge_beams_category(self, beam):
        beam_angle = angle_vectors(beam.centerline.direction, self.stud_direction, deg=True)
        if beam.attributes["edge_index"] in self.interior_segment_indices:
            if beam_angle < 45 or beam_angle > 135:
                beam.attributes["category"] = "edge_stud"
            else:
                beam.attributes["category"] = "header"  #TODO: maybe make this related to interfaces eg. it is header if there is no interface, otherwise plate.
        else:
            if beam_angle < 45 or beam_angle > 135:
                beam.attributes["category"] = "edge_stud"
            else:
                if dot_vectors(self.edge_perpendicular_vectors[beam.attributes["edge_index"]], self.stud_direction) < 0:
                    beam.attributes["category"] = "bottom_plate_beam"
                else:
                    beam.attributes["category"] = "top_plate_beam"


    def _offset_edge_beam(self, beam):
        """Offset elements towards the inside of the wall. The given beam definitions are modified in-place.

        Parameters
        ----------
        element_loop : list of :class:`BeamDefinition`
            The elements to offset.

        """
        vector = -self.edge_perpendicular_vectors[beam.attributes["edge_index"]]
        beam.frame.translate(vector * beam.width * 0.5)
        beam.frame.translate(self.normal * beam.height * 0.5)


    def _apply_linear_cut_to_edge_beam(self, beam):
        """Trim the edge beams to fit between the plate beams."""
        plane = self._slab.edge_planes[beam.attributes["edge_index"]]
        if not TOL.is_zero(dot_vectors(self.normal, plane.normal)):
            long_cut = LongitudinalCutProxy.from_plane_and_beam(self._slab.edge_planes[beam.attributes["edge_index"]], beam)
            beam.add_features(long_cut)


    def _generate_interface_beams(self):
        """Generate the beams for the interface."""
        for interface in self._slab.interfaces:
            if interface.interface_role == "CROSS":
                interface.detail_set.create_elements_cross(interface, self)
            elif interface.interface_role == "MAIN":
                interface.detail_set.create_elements_main(interface, self)
            elif interface.interface_role == "NONE":
                interface.detail_set.create_elements_none(interface, self)

    def _extend_interface_beams(self):
        """extends beams to the interface polyline."""
        for i in range(len(self.outline_a.lines)):
            interface = self.edge_interfaces.get(i, None)
            next_interface = self.edge_interfaces.get((i + 1)%(len(self.outline_a)-1), None)
            if any(interface is None for interface in [interface, next_interface]):
                continue
            ip, ic = intersection_line_line(interface.beams[-1].centerline, next_interface.beams[-1].centerline)
            if ip and ic:
                # if the previous and current edge beams intersect, we extend the previous beam to the intersection point
                interface.beams[-1].length = interface.beams[-1].frame.point.distance_to_point(ip)
                next_interface.beams[-1].length = next_interface.beams[-1].centerline.end.distance_to_point(ic)
                next_interface.beams[-1].frame.point = ic
    # ==========================================================================
    # methods for beam joints
    # ==========================================================================

    def _generate_edge_joints(self):
        for i in range(len(self.outline_a)-1):
            edge_interface_a = self.edge_interfaces.get((i - 1) %(len(self.outline_a)-1), None)
            edge_interface_b = self.edge_interfaces.get(i, None)
            interior_corner = i in self.interior_corner_indices
            if edge_interface_a and len(edge_interface_a.beams) > 1 and edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is an interface, we use the interface to create the joint definition
                self._joints.extend(edge_interface_a.detail_set.create_interface_interface_joints(edge_interface_a, edge_interface_b, self, interior_corner))
            elif edge_interface_a and len(edge_interface_a.beams) > 1:
                # if there is only an interface on the previous edge, we use that to create the joint definition
                self._joints.extend(edge_interface_a.detail_set.create_interface_beam_joint(edge_interface_a, self._edge_beams[i][0], self, interior_corner))
            elif edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is only an interface on the next edge, we use that to create the joint definition
                self._joints.extend(edge_interface_b.detail_set.create_interface_beam_joint(edge_interface_b, self._edge_beams[(i - 1)%(len(self.outline_a)-1)][-1], self, interior_corner))
            else:  # if there is no interface, we create a joint definition between the two edge beams
                self._get_edge_beam_joint(i, interior_corner)

    def _get_edge_beam_joint(self, edge_index, interior_corner):
        beam_a = self._edge_beams[(edge_index - 1)%(len(self.outline_a)-1)][-1]
        beam_b = self._edge_beams[edge_index][0]
        beam_a_angle = angle_vectors(beam_a.centerline.direction, self.stud_direction)
        beam_a_angle = min(beam_a_angle, math.pi - beam_a_angle)  # get the smallest angle to the stud direction
        beam_b_angle = angle_vectors(beam_b.centerline.direction, self.stud_direction)
        beam_b_angle = min(beam_b_angle, math.pi - beam_b_angle)  # get the smallest angle to the stud direction

        if interior_corner:
            if beam_a_angle < beam_b_angle:
                plane = Plane(self._slab.edge_planes[edge_index].point, -self._slab.edge_planes[edge_index].normal)
                joint_def = self.get_joint_from_elements(beam_a, beam_b, butt_plane=plane)
            else:
                plane = Plane(self._slab.edge_planes[edge_index - 1].point, -self._slab.edge_planes[edge_index - 1].normal)
                joint_def = self.get_joint_from_elements(beam_b, beam_a, butt_plane=plane)
        else:
            if beam_a_angle < beam_b_angle:
                joint_def = self.get_joint_from_elements(beam_a, beam_b, back_plane=self._slab.edge_planes[edge_index - 1])
            else:
                joint_def = self.get_joint_from_elements(beam_b, beam_a, back_plane=self._slab.edge_planes[edge_index])

        self._joints.append(joint_def)

    def _generate_face_joints(self):
        """Generate the joint definitions for the face interfaces."""
        for interface in self.face_interfaces:
            detail_set = interface.detail_set
            self._joints.extend(detail_set.create_joints_cross(interface, self))

    def _generate_opening_joints(self):
        """Generate the joint definitions for the openings."""
        for opening in self._openings:
            opening.create_joints()
            self._joints.extend(opening.joints)


    # ==========================================================================
    # methods for stud beams
    # ==========================================================================

    def _generate_openings(self):
        def does_opening_intersect_polyline(opening, polyline):
            """Check if the opening intersects with the polyline."""
            inds = []
            for plate_beam in self.bottom_plate_beams:
                inds.append(plate_beam.attributes["edge_index"])
            for i in list(set(inds)):
                for segment in opening.lines:
                    if intersection_segment_segment(polyline.lines[i], segment, tol=TOL.relative)[0]:
                        return True
            return False


        for opening in self.inner_polylines:
            if does_opening_intersect_polyline(opening, self.frame_outline_a) or does_opening_intersect_polyline(opening, self.frame_outline_b):
                op = Door(opening, self)
            else:
                op = Window(opening, self)
            self._openings.append(op)
            op.create_elements()


    def _generate_stud_beams(self):
        self._generate_studs(min_length=self.beam_dimensions["stud"][0])


    def _get_stud_lines(self):
        stud_lines = []
        x_position = self._config_set.stud_spacing
        frame = Frame(self._slab.frame.point, cross_vectors(self.stud_direction, self.normal), self.stud_direction)
        to_world = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        pts = [pt.transformed(to_world) for pt in self.frame_outline_a.points + self.frame_outline_b.points]
        box = Box.from_points(pts)
        x_position = box.xmin + self._config_set.stud_spacing
        to_local = Transformation.from_frame_to_frame(Frame.worldXY(), frame)
        while x_position < box.xmax - self.beam_dimensions["stud"][0]:
            start_point = Point(x_position, 0, 0)
            start_point.transform(to_local)
            stud_lines.append(Line.from_point_and_vector(start_point, self.stud_direction))
            x_position += self._config_set.stud_spacing
        return stud_lines

    def _generate_studs(self, min_length=0.0):
        stud_lines = self._get_stud_lines()
        for line in stud_lines:
            # get intersections with edge beams and openings and interfaces
            intersections = self._get_stud_intersections(line)
            if not intersections:
                raise ValueError("No intersections found for stud line: {}".format(line))
            else:
                self._generate_and_join_studs_from_intersections(intersections, min_length=min_length)

    def _get_stud_intersections(self, line):
        intersections = []
        beams_to_intersect = []
        for val in self._edge_beams.values():
            beams_to_intersect.extend(val)
        ints = intersection_line_beams(line, beams_to_intersect, max_distance=self.beam_dimensions["stud"][0])
        if ints:
            intersections.extend(ints)
        for opening in self._openings:
            ints = intersection_line_beams(line, [opening.sill, opening.header], max_distance=self.beam_dimensions["stud"][0])
            if ints:
                intersections.extend(ints)
        for interface in self._slab.interfaces:
            if interface.interface_role == "CROSS" and does_line_intersect_polyline(line, interface.beam_polyline):
                ints = intersection_line_beams(line, [interface.beams[0], interface.beams[-1]], max_distance=self.beam_dimensions["stud"][0])
                if ints:
                    intersections.extend(ints)
        return intersections

    def _generate_and_join_studs_from_intersections(self, intersections, min_length=TOL.absolute):
        intersections = sorted(intersections, key=lambda x: x.get("dot"))
        studs = []
        intersecting_beams = []
        for pair in pairwise(intersections):
            # cull the invalid segments but keep the intersectig beams
            seg = Line(pair[0]["point"], pair[1]["point"])

            if self._is_line_in_interface(seg):
                continue
            if self._is_line_in_opening(seg):
                continue

            for intersection in pair:
                if intersection["beam"] not in intersecting_beams:
                    intersecting_beams.append(intersection["beam"])

            if seg.length < min_length:
                continue
            if not is_point_in_polyline(seg.point_at(0.5), self.frame_outline_a):
                continue
            # create the beam element and add joints
            studs.append(beam_from_category(self, seg, "stud"))
            while len(intersecting_beams) > 0:
                beam = intersecting_beams.pop()
                self._joints.append(self.get_joint_from_elements(studs[-1], beam))

        if len(studs) > 0:  # add joints with any leftover beams
            while len(intersecting_beams) > 0:
                beam = intersecting_beams.pop()
                self._joints.append(self.get_joint_from_elements(studs[-1], beam))
            self.studs.extend(studs)

    def _is_line_in_interface(self, line):
        for i in self._slab.interfaces:
            if i.interface_role == "CROSS" and is_point_in_polyline(line.point_at(0.5), i.beam_polyline, in_plane=False):
                return True
        return False

    def _is_line_in_opening(self, line):
        for opening in self._openings:
            if is_point_in_polyline(line.point_at(0.5), opening.frame_polyline, in_plane=False):
                return True
        return False



    def _cull_overlaps(self):
        not_studs = [beam for beam in self.beams if beam.attributes.get("category", None) != "stud"]
        for stud in self.studs:
            for other_element in not_studs:
                if (
                    self._distance_between_elements(stud, other_element)
                    < (self.beam_dimensions[stud.attributes["category"]][0] + self.beam_dimensions[other_element.attributes["category"]][0]) / 2
                ):
                    self.studs.remove(stud)
                    break

    def _distance_between_elements(self, element_one, element_two):
        pt = element_one.centerline.point_at(0.5)
        cp = closest_point_on_segment(pt, element_two.centerline)
        return pt.distance_to_point(cp)

    def _generate_plates(self):
        if self._config_set.sheeting_inside:
            self.plates.append(Plate(self.outline_a, self.frame_outline_a, openings=self.inner_polylines))
        if self._config_set.sheeting_outside:
            self.plates.append(Plate(self.outline_b, self.frame_outline_b, openings=self.inner_polylines))


def intersection_line_beams(line, beams, max_distance=0.0):
    intersections = []
    for beam in beams:
        line_pt, beam_pt = intersection_line_line(line, beam.centerline)
        if line_pt:
            if distance_point_point(beam_pt, closest_point_on_segment(beam_pt, beam.centerline)) > max_distance:
               continue
            intersection = {}
            intersection["point"] = Point(*line_pt)
            intersection["dot"] = dot_vectors(Vector.from_start_end(line.point_at(0.5), Point(*line_pt)), line.direction)
            intersection["beam"] = beam
            intersections.append(intersection)
    return intersections

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



def does_line_intersect_polyline(line, polyline):
    """Find the intersection points between a line and a polyline.

    Parameters
    ----------
    line : :class:`Line`
        The line to intersect with the polyline.
    polyline : :class:`Polyline`
        The polyline to intersect with the line.
    in_plane : bool, optional
        If True, the intersection is computed in the plane of the polyline.
        Default is True.

    Returns
    -------
    list of :class:`Point`
        The intersection points between the line and the polyline.
    """
    for segment in polyline.lines:
        intersection = intersection_line_segment(line, segment)
        if intersection:
            return True
    return False

def split_beam(beam, interval, joints):
    """Split a beam into segments at specified intervals.

    Parameters
    ----------
    beam : :class:`~compas_timber.parts.Beam`
        The beam to split.
    interval : tuple(float, float)
        The range in model units to remove from the beam.
    joints : list of :class:`~compas_timber.connections.Joint`
        List of joints which the method should parse to remove or copy to new beam.

    Returns
    -------
    list of :class:`~compas_timber.parts.Beam`
        The list of split beams.
    list of :class:`~compas_timber.connections.Joint`
        The list of joints associated with the split beams.

    """
    joints = [j for j in joints if beam in j.elements]
    other_beams = []
    for joint in joints:
        for element in joint.elements:
            if element != beam and isinstance(element, Beam):
                other_beams.append(element)
    joint_locations = [distance_segment_segment_points(beam.centerline, other_beam.centerline)[0] for other_beam in other_beams]
    joint_dots = [dot_vectors(beam.centerline.direction, Vector.from_start_end(beam.centerline.start, joint_location)) for joint_location in joint_locations]



    new_beam = beam.copy()
    new_beam.attributes.update(beam.attributes)
    beam.length = interval[0]
    new_beam.length = beam.length - interval[1]
    new_beam.frame.translate(beam.frame.xaxis * interval[1])

    for joint, dot in zip(joints, joint_dots):
        if dot < interval[0]:
            continue
        elif dot < interval[1]:
            joints.remove(joint)
        else:
            joint.elements.remove(beam)
            new_joint = joint.copy()
            new_joint.elements = [new_beam]
            joints.append(new_joint)
