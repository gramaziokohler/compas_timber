import math

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
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import is_parallel_vector_vector
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication.longitudinal_cut import LongitudinalCutProxy
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import intersection_line_beams


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


class SlabPopulatorConfigurationSet(object):
    """Contains one or more configuration set for the WallPopulator.

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

    def __str__(self):
        return "SlabPopulatorConfigurationSet({}, {}, {})".format(self.stud_spacing, self.beam_width, self.stud_direction)

    @classmethod
    def default(cls, stud_spacing, beam_width):
        return cls(stud_spacing, beam_width)

    @property
    def beam_widths(self):
        """Returns the custom dimensions from the configuration set."""
        for key in self.BEAM_CATEGORY_NAMES:
            self._beam_widths[key] = self._config_set.beam_width
        if self._config_set.custom_dimensions:
            dimensions = self._config_set.custom_dimensions
            for key, value in dimensions.items():
                if value:
                    self._beam_widths[key] = value
        return self._beam_widths

class SlabPopulator(object):
    """Create a timber assembly from a surface.

    Parameters
    ----------
    configuration_set : :class:`WallPopulatorConfigurationSet`
        The configuration for this wall populator.
    slab : :class:`compas_timber.elements.Slab`
        The slab for this populater to fill with beams.

    Attributes
    ----------
    outline_a : :class:`compas.geometry.Polyline`
        The outline A of the slab.
    outline_b : :class:`compas.geometry.Polyline`
        The outline B of the slab.
    openings : list of :class:`compas.geometry.Polyline`
        The openings in the slab.
    opening_polylines : list of :class:`compas.geometry.Polyline`
        The opening polylines of the slab.
    frame : :class:`compas.geometry.Polyline`
        The frame of the slab.
    interfaces : list of :class:`compas_timber.connections.SlabToSlabInterface`
        The interfaces of the slab. These are the connections to other slabs.
    edge_count : int
        The number of edges in the slab outline.
    stud_spacing : float
        The spacing between studs in the slab.
    stud_direction : :class:`compas.geometry.Vector`
        The direction of the studs in the slab.
    tolerance : :class:`compas_tolerance.Tolerance`
        The tolerance for the slab populator.
    sheeting_outside : float
        The outside sheeting thickness from the configuration set.
    sheeting_inside : float
        The inside sheeting thickness from the configuration set.
    frame_outline_a : :class:`compas.geometry.Polyline`
        The outline A of the frame.
    frame_outline_b : :class:`compas.geometry.Polyline`
        The outline B of the frame.
    frame_thickness : float
        The thickness of the frame. This is the thickness of the slab minus the sheeting thicknesses.


    """

    BEAM_CATEGORY_NAMES = ["stud", "edge_stud", "top_plate_beam", "bottom_plate_beam","header","sill","king_stud","jack_stud", "detail"]

    def __init__(self, configuration_set, slab):
        self._slab = slab
        self._config_set = configuration_set

        self._stud_direction = None
        self._beam_dimensions = None
        self._frame_outline_a = None
        self._frame_outline_b = None
        self._frame_thickness = None

        self.plates = []
        self.studs = []
        self._interior_corner_indices = []
        self._edge_perpendicular_vectors = []
        self._edge_beams = {}
        self.joints = []
        self._rules = []

    @property
    def opening_polylines(self):
        """Returns the opening polylines of the slab."""
        return [op.outline for op in self._slab.openings]

    @property
    def edge_count(self):
        """Returns the number of edges in the slab outline."""
        return len(self._slab.outline_a) - 1

    @property
    def stud_direction(self):
        """Returns the stud direction from the configuration set."""
        if self._stud_direction is None:
            if self._config_set.stud_direction:
                if is_parallel_vector_vector(self._slab.frame.normal, self._config_set.stud_direction):
                    self._stud_direction = self._slab.frame.yaxis
                else:
                    proj = Projection.from_plane(Plane.from_frame(self._slab.frame))
                    self._stud_direction = self._config_set.stud_direction.transformed(proj)
        return self._stud_direction


    @property
    def frame_outline_a(self):
        """Returns the frame outline A, adjusted for sheeting."""
        if self._frame_outline_a is None:
            self._handle_sheeting_offsets()
        return self._frame_outline_a

    @property
    def frame_outline_b(self):
        """Returns the frame outline B, adjusted for sheeting."""
        if self._frame_outline_b is None:
            self._handle_sheeting_offsets()
        return self._frame_outline_b

    @property
    def thickness(self):
        """Returns the thickness of the slab."""
        return self._slab.thickness

    @property
    def frame_thickness(self):
        """Returns the frame thickness, adjusted for sheeting."""
        if self._frame_thickness is None:
            self._handle_sheeting_offsets()
        return self._frame_thickness

    @property
    def beam_dimensions(self):
        """Returns the custom dimensions from the configuration set."""
        if self._beam_dimensions is None:
            self._beam_dimensions = {}
            for key in self.BEAM_CATEGORY_NAMES:
                self._beam_dimensions[key] = (self._config_set.beam_width, self.frame_thickness)
            if self._config_set.custom_dimensions:
                dimensions = self._config_set.custom_dimensions
                for key, value in dimensions.items():
                    if value:
                        self._beam_dimensions[key] = (value[0], self.frame_thickness)
        return self._beam_dimensions

    def __repr__(self):
        return "SlabPopulator({}, {})".format(self._config_set, self._slab)

    @property
    def elements(self):
        return self.beams + self.plates

    @property
    def beams(self):
        beams = self.edge_beams
        for interface in self._slab.interfaces:
            beams.extend(interface.beams)
        for opening in self._slab.openings:
            beams.extend(opening.beams)
        beams.extend(self.studs)
        return list(set(beams))

    @property
    def edge_perpendicular_vectors(self):
        """Returns the perpendicular vectors for the edges of the slab."""
        if not self._edge_perpendicular_vectors:
            self._edge_perpendicular_vectors = [get_polyline_segment_perpendicular_vector(self._slab.outline_a, i) for i in range(self.edge_count)]
        return self._edge_perpendicular_vectors



    @property
    def edge_beams(self):
        """Returns the edge beams of the slab."""
        beams = []
        for val in self._edge_beams.values():
            beams.extend(val)
        return beams

    @property
    def edge_studs(self):
        return [beam for beam in self.edge_beams if beam.attributes.get("category", None) == "edge_stud"]

    @property
    def top_plate_beams(self):
        return [beam for beam in self.edge_beams if beam.attributes.get("category", None) == "top_plate_beam"]

    @property
    def bottom_plate_beams(self):
        return [beam for beam in self.edge_beams if beam.attributes.get("category", None) == "bottom_plate_beam"]

    @property
    def interior_corner_indices(self):
        """Get the indices of the interior corners of the slab outline."""
        if not self._interior_corner_indices:
            """Get the indices of the interior corners of the slab outline."""
            points = self._slab.outline_a.points[0:-1]
            cw = is_polyline_clockwise(self._slab.outline_a, self._slab.frame.normal)
            for i in range(len(points)):
                angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], self._slab.frame.normal, deg=True)
                if not (cw ^ (angle < 0)):
                    self._interior_corner_indices.append(i)
        return self._interior_corner_indices

    @property
    def interior_segment_indices(self):
        """Get the indices of the interior segments of the slab outline."""
        for i in range(self.edge_count):
            if i in self.interior_corner_indices and (i + 1) % self.edge_count in self.interior_corner_indices:
                yield i

    @property
    def edge_interfaces(self):
        """Get the edge interfaces of the slab."""
        interfaces = {}
        for interface in self._slab.interfaces:
            if interface.edge_index is not None:
                interfaces[interface.edge_index] = interface
        return interfaces

    @property
    def face_interfaces(self):
        """Get the face interfaces of the slab."""
        return [i for i in self._slab.interfaces if i.edge_index is None]

    @property
    def _default_rules(self):
        return [
            CategoryRule(TButtJoint, "stud", "top_plate_beam"),
            CategoryRule(LButtJoint, "edge_stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "stud", "bottom_plate_beam"),
            CategoryRule(LButtJoint, "edge_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "stud", "edge_stud"),
            CategoryRule(TButtJoint, "stud", "detail"),
            CategoryRule(TButtJoint, "jack_stud", "detail"),
            CategoryRule(TButtJoint, "king_stud", "detail"),
            CategoryRule(TButtJoint, "header", "king_stud"),
            CategoryRule(TButtJoint, "sill", "king_stud"),
            CategoryRule(TButtJoint, "sill", "jack_stud"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "king_stud", "edge_stud"),
            CategoryRule(TButtJoint, "jack_stud", "edge_stud"),


        ]

    @property
    def rules(self):
        if not self._rules:
            self._rules = self._default_rules
            if self._config_set.joint_overrides:
                for rule in self._config_set.joint_overrides:
                    rule_set = set([rule.category_a, rule.category_b])
                    for i, _rule in enumerate(self._rules):
                        _set = set([_rule.category_a, _rule.category_b])
                        if rule_set == _set:
                            self._rules[i] = rule
                            break
        return self._rules

    @classmethod
    def beam_category_names(cls):
        return SlabPopulator.BEAM_CATEGORY_NAMES

    @classmethod
    def from_model(cls, model, configuration_sets):
        # type: (TimberModel, List[WallPopulatorConfigurationSet]) -> List[WallPopulator]
        """matches configuration sets to walls and returns a list of SlabPopulator instances, each per wall"""
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

    def _handle_sheeting_offsets(self):
        """Handles the sheeting offsets for the slab outlines."""
        """This method creates new outlines for the beam frame based on the sheeting thicknesses."""
        self._frame_thickness = self.thickness
        if self._config_set.sheeting_inside:
            offset_inside = self._config_set.sheeting_inside / self.thickness
            pts_inside = []
            for pt_a, pt_b in zip(self._slab.outline_a.points, self._slab.outline_b.points):
                pt = pt_a * (1 - offset_inside) + pt_b * offset_inside
                pts_inside.append(pt)
            self._frame_thickness -= self._config_set.sheeting_inside
            self._frame_outline_a = Polyline(pts_inside)
            for polyline in self.opening_polylines:
                for pt in polyline.points:
                    pt.translate(self._slab.frame.normal * self._config_set.sheeting_inside)
        else:
            self._frame_outline_a = self._slab.outline_a
        if self._config_set.sheeting_outside:
            offset_outside = self._config_set.sheeting_outside / self.thickness
            pts_outside = []
            for pt_a, pt_b in zip(self._slab.outline_a.points, self._slab.outline_b.points):
                pts_outside.append(pt_a * offset_outside + pt_b * (1 - offset_outside))
            self._frame_thickness -= self._config_set.sheeting_outside
            self._frame_outline_b = Polyline(pts_outside)
        else:
            self._frame_outline_b = self._slab.outline_b

    def create_elements(self):
        """Does the actual populating of the wall
        creates and returns all the elements in the wall, returns also the joint definitions
        """
        self._generate_edge_beams()
        self._generate_studs()
        self._generate_interface_beams()
        self._extend_interior_corner_beams()
        self._generate_opening_beams()
        self._cull_and_split_studs()
        self._generate_plates()
        return self.elements

    def generate_joints(self):
        self._generate_edge_joints()
        self._generate_face_interface_joints()
        self._generate_opening_joints()
        return self.joints

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
            beam = Beam.from_centerline(seg, width=width + min_width, height=self.frame_thickness, z_vector=self._slab.frame.normal)
            beam.attributes["edge_index"] = i
            self._set_edge_beams_category(beam)
            self._offset_edge_beam(beam)
            self._apply_linear_cut_to_edge_beam(beam)
            self._edge_beams[i] = [beam]

    def _get_edge_segments_and_widths(self):
        edge_segs = []
        edge_beam_widths = []
        for i in range(self.edge_count):
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
            return seg_b.translated(-self._slab.frame.normal * self.frame_thickness), dot

    def _set_edge_beams_category(self, beam):
        beam_angle = angle_vectors(beam.centerline.direction, self.stud_direction, deg=True)
        if beam.attributes["edge_index"] in self.interior_segment_indices:
            if beam_angle < 45 or beam_angle > 135:
                beam.attributes["category"] = "edge_stud"
            else:
                beam.attributes["category"] = "header"  # TODO: maybe make this related to interfaces eg. it is header if there is no interface, otherwise plate.
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
        beam.frame.translate(self._slab.frame.normal * beam.height * 0.5)

    def _apply_linear_cut_to_edge_beam(self, beam):
        """Trim the edge beams to fit between the plate beams."""
        plane = self._slab.edge_planes[beam.attributes["edge_index"]]
        if not TOL.is_zero(dot_vectors(self._slab.frame.normal, plane.normal)):
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

    def _extend_interior_corner_beams(self):
        """Extend the beams at the interior corners to ensure that stud generation creates valid intersections."""
        for i in range(self.edge_count):
            edge_interface_a = self.edge_interfaces.get((i - 1) % self.edge_count, None)
            edge_interface_b = self.edge_interfaces.get(i, None)
            # interface.beams: last beam is innermost. _edge_beams[edge_index]: first beam is first on the edge.
            beam_a = edge_interface_a.beams[-1] if edge_interface_a else self._edge_beams[(i - 1) % self.edge_count][-1]
            beam_b = edge_interface_b.beams[-1] if edge_interface_b else self._edge_beams[i][0]
            ip, ic = intersection_line_line(beam_a.centerline, beam_b.centerline)
            if ip and ic:
                beam_a.length = beam_a.frame.point.distance_to_point(ip)
                beam_b.length = beam_b.centerline.end.distance_to_point(ic)
                beam_b.frame.point = ic

    # ==========================================================================
    # methods for beam joints
    # ==========================================================================

    def _generate_edge_joints(self):
        """Generate the joint definitions for the slab edges. When there is an interface, we use the interface.detail_set to create the joint definition."""
        for i in range(self.edge_count):
            edge_interface_a = self.edge_interfaces.get((i - 1) % self.edge_count, None)
            edge_interface_b = self.edge_interfaces.get(i, None)
            interior_corner = i in self.interior_corner_indices
            if edge_interface_a and len(edge_interface_a.beams) > 1 and edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is an interface, we use the interface to create the joint definition
                self.joints.extend(edge_interface_a.detail_set.create_interface_interface_joints(edge_interface_a, edge_interface_b, self, interior_corner))
            elif edge_interface_a and len(edge_interface_a.beams) > 1:
                # if there is only an interface on the previous edge, we use that to create the joint definition
                self.joints.extend(edge_interface_a.detail_set.create_interface_beam_joint(edge_interface_a, self._edge_beams[i][0], self, interior_corner))
            elif edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is only an interface on the next edge, we use that to create the joint definition
                self.joints.extend(
                    edge_interface_b.detail_set.create_interface_beam_joint(edge_interface_b, self._edge_beams[(i - 1) % self.edge_count][-1], self, interior_corner)
                )
            else:  # if there is no interface, we create a joint definition between the two edge beams
                self._generate_edge_beam_joint(i, interior_corner)

    def _generate_edge_beam_joint(self, edge_index, interior_corner):
        """Generate the joint definition between two edge beams. Used when there is no interface on either edge."""
        beam_a = self._edge_beams[(edge_index - 1) % self.edge_count][-1]
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

        self.joints.append(joint_def)

    def _generate_face_interface_joints(self):
        """Generate the joint definitions for the face interfaces."""
        for interface in self.face_interfaces:
            detail_set = interface.detail_set
            self.joints.extend(detail_set.create_joints_cross(interface, self))

    def _generate_opening_joints(self):
        """Generate the joint definitions for the openings."""
        for opening in self._slab.openings:
            self.joints.extend(opening.generate_joints(self))

    # ==========================================================================
    # methods for stud beams
    # ==========================================================================

    def _generate_opening_beams(self):
        """Generates the elements for the openings."""
        print("there are {} openings in the slab".format(len(self._slab.openings)))

        for opening in self._slab.openings:
            print("GENERATING OPENING BEAMS")
            opening.generate_elements(self)
            # opening.detail_set.cull_and_split_studs(opening, self)


    def _cull_and_split_studs(self):
        """Culls the studs that are too short and trims the studs that are too long."""
        for interface in self._slab.interfaces:
            if interface.interface_role == "CROSS":
                interface.detail_set.cull_and_split_studs(interface, self)
        for opening in self._slab.openings:
            opening.detail_set.cull_and_split_studs(opening, self)

    def _generate_studs(self, min_length=0.0):
        """Generates the stud beams."""
        min_length = self.beam_dimensions["stud"][0]
        stud_lines = self._get_stud_lines()
        for line in stud_lines:
            # get intersections with edge beams and openings and interfaces
            intersections = self._get_stud_intersections(line)
            if not intersections:
                raise ValueError("No intersections found for stud line: {}".format(line))
            else:
                # generate studs from intersections
                self._generate_studs_from_intersections(intersections, min_length=min_length)

    def _get_stud_lines(self):
        """Generates the stud lines based on the frame outlines and stud direction."""
        stud_lines = []
        x_position = self._config_set.stud_spacing
        frame = Frame(self._slab.frame.point + self._slab.frame.normal * self._config_set.sheeting_inside, cross_vectors(self.stud_direction, self._slab.frame.normal), self.stud_direction)
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

    def _get_stud_intersections(self, line):
        """collects all the beams that intersect with the given line and returns the intersection points"""
        beams_to_intersect = []
        for val in self._edge_beams.values():
            beams_to_intersect.extend(val)
        # for opening in self._slab.openings:
        #     beams_to_intersect.extend([opening.sill, opening.header])
        # for interface in self._slab.interfaces:
        #     beams_to_intersect.extend(interface.beams)
        # beams_to_intersect = list(set(beams_to_intersect))  # remove duplicates
        return intersection_line_beams(line, beams_to_intersect, max_distance=self.beam_dimensions["stud"][0])

    def _generate_studs_from_intersections(self, intersections, min_length=TOL.absolute):
        """parses the intersections and creates stud beams from them"""
        intersections = sorted(intersections, key=lambda x: x.get("dot"))
        studs = []
        intersecting_beams = []
        for pair in pairwise(intersections):
            # cull the invalid segments but keep the intersectig beams
            seg = Line(pair[0]["point"], pair[1]["point"])
            # if self._is_line_in_interface(seg):
            #     continue
            # if self._is_line_in_opening(seg):
            #     continue

            for intersection in pair:
                if intersection["beam"] not in intersecting_beams:
                    intersecting_beams.append(intersection["beam"])

            if seg.length < min_length:
                continue
            if not is_point_in_polyline(seg.point_at(0.5), self.frame_outline_a, in_plane=False):
                continue
            # create the beam element and add joints
            stud = beam_from_category(self, seg, "stud")
            if stud is not None:
                self.studs.append(stud)
        #     while len(intersecting_beams) > 0:
        #         beam = intersecting_beams.pop()
        #         self.joints.append(self.get_joint_from_elements(studs[-1], beam))
        # if len(studs) > 0:  # add joints with any leftover beams
        #     while len(intersecting_beams) > 0:
        #         beam = intersecting_beams.pop()
        #         self.joints.append(self.get_joint_from_elements(studs[-1], beam))


    def _is_line_in_interface(self, line):
        for i in self._slab.interfaces:
            if i.interface_role == "CROSS" and is_point_in_polyline(line.point_at(0.5), i.beam_polyline, in_plane=False):
                return True
        return False

    # def _is_line_in_opening(self, line):
    #     for opening in self._slab.openings:
    #         if is_point_in_polyline(line.point_at(0.5), opening.frame_polyline, in_plane=False):
    #             return True
    #     return False

    def _cull_overlaps(self):  # TODO: use RTree or similar to speed this up
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
            self.plates.append(Plate(self._slab.outline_a, self.frame_outline_a, opening_outlines=self.opening_polylines))
        if self._config_set.sheeting_outside:
            self.plates.append(Plate(self._slab.outline_b, self.frame_outline_b, opening_outlines=self.opening_polylines))



def beam_from_category(beam_dimensions, segment, category, normal, normal_offset=True, **kwargs):
    """Creates a beam from a segment and a category, using the dimensions from the configuration set.
    Parameters
    ----------
    parent : :class:`SlabPopulator` or class:`Window`
        The parent object containing the configuration set and slab.
    segment : :class:`compas.geometry.Line`
        The segment to create the beam from.
    category : str
        The category of the beam, which determines its dimensions.
    normal_offset : bool, optional
        Whether to offset the beam by 1/2 of the beam height in the parent.normal direction. Defaults to True.
    kwargs : dict, optional
        Additional attributes to set on the beam.

    Returns
    -------
    :class:`compas_timber.elements.Beam`
        The created beam with the specified category and attributes.
    """
    if category not in slab_populator.beam_dimensions:
        raise ValueError(f"Unknown beam category: {category}")
    width = beam_dimensions[category][0]
    height = frame_thickness
    beam = Beam.from_centerline(segment, width=width, height=height, z_vector=slab_populator._slab.frame.normal)
    if normal_offset:
        beam.frame.translate(slab_populator._slab.frame.normal * height * 0.5)  # align the beam to the slab frame
    beam.attributes["category"] = category
    for key, value in kwargs.items():
        beam.attributes[key] = value
    if beam is None:
        raise ValueError("Failed to create beam from segment: {}".format(segment))
    return beam
