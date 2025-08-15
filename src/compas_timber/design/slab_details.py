import math

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber import elements
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.design.details import DetailBase
from compas_timber.elements import Beam, beam, slab
from compas_timber.elements import Plate
from compas_timber.fabrication.longitudinal_cut import LongitudinalCutProxy
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import intersection_line_beams
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import is_polyline_clockwise


class SlabDetailBase(DetailBase):
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
        Custom cross section for the beams, by category. (e.g. {"bottom_plate_beam": (120, 60)})
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
        sheeting_outside=0,
        sheeting_inside=0,
        beam_width_overrides=None,
        joint_overrides=None,
    ):
        super(SlabDetailBase, self).__init__(beam_width_overrides, joint_overrides)
        self.stud_spacing = stud_spacing
        self.beam_width = beam_width
        self.stud_direction = stud_direction
        self.sheeting_outside = sheeting_outside
        self.sheeting_inside = sheeting_inside

    def __str__(self):
        return "SlabDetailSet({}, {}, {})".format(self.stud_spacing, self.beam_width, self.stud_direction)

    @classmethod
    def default(cls, stud_spacing, beam_width):
        return cls(stud_spacing, beam_width)

    def prepare_populator(self, slab_populator):
        """Prepares the slab populator by setting up necessary attributes."""
        self._set_frame_outlines(slab_populator)

    def create_elements(self, slab_populator):
        """Generates the elements for the slab."""
        raise NotImplementedError("This method should be implemented in a subclass.")

    def create_joints(self, slab_populator):
        """Generates the joints for the slab."""
        raise NotImplementedError("This method should be implemented in a subclass.")

    # ==========================================================================
    # methods for preparaing slab populator
    # ==========================================================================

    def _set_frame_outlines(self, slab_populator):
        """Handles the sheeting offsets for the slab outlines."""
        """This method creates new outlines for the beam frame based on the sheeting thicknesses."""
        if not self.sheeting_inside:
            slab_populator.frame_outline_a = slab_populator.outline_a
        else:
            offset_inside = self.sheeting_inside / slab_populator.thickness
            pts_inside = []
            for pt_a, pt_b in zip(slab_populator.outline_a.points, slab_populator.outline_b.points):
                pt = pt_a * (1 - offset_inside) + pt_b * offset_inside
                pts_inside.append(pt)
            slab_populator.frame_outline_a = Polyline(pts_inside)

        if not self.sheeting_outside:
            slab_populator.frame_outline_b = slab_populator.outline_b
        else:
            offset_outside = self.sheeting_outside / slab_populator.thickness
            pts_outside = []
            for pt_a, pt_b in zip(slab_populator.outline_a.points, slab_populator.outline_b.points):
                pts_outside.append(pt_a * offset_outside + pt_b * (1 - offset_outside))

            slab_populator.frame_outline_b = Polyline(pts_outside)
    # ==========================================================================
    # methods for edge beams
    # ==========================================================================

    def _create_edge_beams(self, slab_populator, min_width=None, standardize_blank_dimension=False):
        """Get the edge beam definitions for the outer polyline of the slab."""
        if min_width is None:
            min_width = self.beam_width
        edge_segs, edge_offset = self._get_edge_segments_and_widths(slab_populator)
        elements = []
        for i, (seg, width) in enumerate(zip(edge_segs, edge_offset)):
            offset = None
            if standardize_blank_dimension:
                offset = 2 * width + min_width
                width = math.ceil(width / 20) * 20  # round up to the nearest 20mm
                offset -= width

            beam = Beam.from_centerline(seg, width=width + min_width, height=slab_populator.frame_thickness, z_vector=Vector(0, 0, 1))
            beam.attributes["edge_index"] = i
            self._set_edge_beam_category(slab_populator, beam)
            self._offset_edge_beam(beam, slab_populator, distance=offset)
            self._apply_linear_cut_to_edge_beam(beam, slab_populator)
            elements.append(beam)
        print("Edge beams created:", elements)
        return elements

    def _get_edge_segments_and_widths(self, slab_populator):
        edge_segs = []
        edge_beam_widths = []
        for i in range(len(slab_populator.frame_outline_a) - 1):
            seg, width = self._get_outer_segment_and_offset(slab_populator, i)
            edge_segs.append(seg)
            edge_beam_widths.append(width)
        return edge_segs, edge_beam_widths

    def _get_outer_segment_and_offset(self, slab_populator, segment_index):
        vector = slab_populator.edge_perpendicular_vectors[segment_index]
        seg_a = slab_populator.frame_outline_a.lines[segment_index]
        seg_b = slab_populator.frame_outline_b.lines[segment_index]
        dot = dot_vectors(vector, Vector.from_start_end(seg_a.start, seg_b.start))
        if dot <= 0:  # seg_b is closer to the middle
            return Line(Point(seg_a.start[0], seg_a.start[1], 0), Point(seg_a.end[0], seg_a.end[1], 0)), -dot
        else:  # seg_a is closer to the middle
            return Line(Point(seg_b.start[0], seg_b.start[1], 0), Point(seg_b.end[0], seg_b.end[1], 0)), dot

    def _set_edge_beam_category(self, slab_populator, beam):
        if abs(beam.centerline.direction[0]) < abs(beam.centerline.direction[1]):
            beam.attributes["category"] = "edge_stud"
        else:
            if dot_vectors(slab_populator.edge_perpendicular_vectors[beam.attributes["edge_index"]], Vector(0, 0, 1)) < 0:
                beam.attributes["category"] = "bottom_plate_beam"
            else:
                beam.attributes["category"] = "top_plate_beam"

    def _offset_edge_beam(self, beam, slab_populator, distance=None):
        """Offset elements towards the inside of the wall. The given beam definitions are modified in-place.

        Parameters
        ----------
        element_loop : list of :class:`BeamDefinition`
            The elements to offset.

        """
        vector = slab_populator.edge_perpendicular_vectors[beam.attributes["edge_index"]]
        if distance is None:
            distance = beam.width * 0.5
        beam.frame.translate(-vector * distance)

    def _apply_linear_cut_to_edge_beam(self, beam, slab_populator):
        """Trim the edge beams to fit between the plate beams."""
        plane = slab_populator.edge_planes[beam.attributes["edge_index"]]
        if not TOL.is_zero(dot_vectors(Vector(0, 0, 1), plane.normal)):
            long_cut = LongitudinalCutProxy.from_plane_and_beam(plane, beam)
            beam.add_features(long_cut)

    # ==========================================================================
    # methods to trim and cull beams
    # ==========================================================================




    def _extend_interior_corner_beams(self, slab_populator):
        """Extend the beams at the interior corners to ensure that stud generation creates valid intersections."""
        for i in range(slab_populator.edge_count):
            edge_interface_a = slab_populator.edge_interfaces.get((i - 1) % slab_populator.edge_count, None)
            edge_interface_b = slab_populator.edge_interfaces.get(i, None)
            # interface.beams: last beam is innermost. edge_beams[edge_index]: first beam is first on the edge.
            if edge_interface_a:
                beam_a = edge_interface_a[0].beams[-1]
            else:
                beam_a = slab_populator.edge_beams.get((i - 1) % slab_populator.edge_count)[-1]
            if edge_interface_b:
                beam_b = edge_interface_b[0].beams[-1]
            else:
                beam_b = slab_populator.edge_beams.get(i)[0]
            ip, ic = intersection_line_line(beam_a.centerline, beam_b.centerline)
            if ip and ic:
                beam_a.length = beam_a.frame.point.distance_to_point(ip)
                beam_b.length = beam_b.centerline.end.distance_to_point(ic)
                beam_b.frame.point = ic

    # ==========================================================================
    # methods for beam joints
    # ==========================================================================

    def _create_edge_joints(self, slab_populator):
        """Generate the joint definitions for the slab edges. When there is an interface, we use the interface.detail_set to create the joint definition."""
        direct_rules = []
        for i in range(slab_populator.edge_count):
            edge_interface_a = slab_populator.edge_interfaces.get((i - 1) % slab_populator.edge_count, None)
            edge_interface_a = edge_interface_a[0] if edge_interface_a else None #TODO consider whether we can have multiple interfaces on one edge.
            edge_interface_b = slab_populator.edge_interfaces.get(i, None)
            edge_interface_b = edge_interface_b[0] if edge_interface_b else None #TODO consider whether we can have multiple interfaces on one edge.
            interior_corner = False
            points = slab_populator.frame_outline.points[0:-1]
            cw = is_polyline_clockwise(points, Vector(0, 0, 1))
            angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], Vector(0, 0, 1), deg=True)
            if not (cw ^ (angle < 0)):
                interior_corner = True
            if edge_interface_a and len(edge_interface_a.beams) > 1 and edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is an interface, we use the interface to create the joint definition
                direct_rules.extend(edge_interface_a.detail_set.create_interface_interface_joints(edge_interface_a, edge_interface_b, slab_populator, interior_corner))
            elif edge_interface_a and len(edge_interface_a.beams) > 1:
                # if there is only an interface on the previous edge, we use that to create the joint definition
                direct_rules.extend(edge_interface_a.detail_set.create_interface_beam_joint(edge_interface_a, slab_populator.edge_beams[i][0], slab_populator, interior_corner))
            elif edge_interface_b and len(edge_interface_b.beams) > 1:
                # if there is only an interface on the next edge, we use that to create the joint definition
                direct_rules.extend(edge_interface_b.detail_set.create_interface_beam_joint(edge_interface_b, slab_populator.edge_beams[(i - 1) % slab_populator.edge_count][-1], slab_populator, interior_corner))
            else:  # if there is no interface, we create a joint definition between the two edge beams
                direct_rules.extend(self._create_edge_beam_joint(i, interior_corner))
        return direct_rules

    def _create_edge_beam_joint(self, slab_populator, corner_index, interior_corner):
        """Generate the joint definition between two edge beams. Used when there is no interface on either edge."""
        beam_a = slab_populator.edge_beams[(corner_index - 1) % slab_populator.edge_count][-1]
        beam_b = slab_populator.edge_beams[corner_index][0]
        beam_a_slope = abs(beam_a.frame.xaxis[1]/beam_a.frame.xaxis[0])
        beam_b_slope = abs(beam_b.frame.xaxis[1]/beam_b.frame.xaxis[0])

        if interior_corner:
            if beam_a_slope < beam_b_slope:
                plane = Plane(slab_populator.edge_planes[corner_index].point, -slab_populator.edge_planes[corner_index].normal)
                direct_rule = self.get_direct_rule_from_elements(beam_a, beam_b, butt_plane=plane)
            else:
                plane = Plane(slab_populator.edge_planes[corner_index - 1].point, -slab_populator.edge_planes[corner_index - 1].normal)
                direct_rule = self.get_direct_rule_from_elements(beam_b, beam_a, butt_plane=plane)
        else:
            if beam_a_slope < beam_b_slope:
                direct_rule = self.get_direct_rule_from_elements(beam_a, beam_b, back_plane=slab_populator.edge_planes[corner_index - 1])
            else:
                direct_rule = self.get_direct_rule_from_elements(beam_b, beam_a, back_plane=slab_populator.edge_planes[corner_index])

        return direct_rule

    # ==========================================================================
    # methods for stud beams
    # ==========================================================================

    def _create_studs(self, slab_populator, min_length=0.0):
        """Generates the stud beams."""
        min_length = self.beam_width_overrides.get("stud", None) or self.beam_width
        x_position = self.stud_spacing
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        studs = []
        while x_position < slab_populator.obb.xmax - beam_dimensions["stud"][0]:
            # get intersections with edge beams and openings and interfaces
            intersections = intersection_line_beams(
                Line(Point(x_position, 0, 0), Point(x_position, 1, 0)),
                [b for b in slab_populator.elements if b.attributes.get("edge_index", None) is not None],
                max_distance=self.beam_width
                )

            if not intersections:
                raise ValueError("No intersections found for stud line at x = {}".format(x_position))

            intersections = sorted(intersections, key=lambda x: x.get("dot"))
            for pair in pairwise(intersections):
                if pair[0]["point"].distance_to_point(pair[1]["point"]) < min_length:
                    continue
                if not is_point_in_polyline((pair[0]["point"] + pair[1]["point"])/2, slab_populator.frame_outline, in_plane=False):
                    continue
                studs.append(self.beam_from_category(Line(pair[0]["point"], pair[1]["point"]), "stud", slab_populator))
            x_position += self.stud_spacing
        return studs

    def _get_stud_lines(self, slab_populator):
        """Generates the stud lines based on the frame outlines and stud direction."""




    def _get_stud_intersections(self, slab_populator, line):
        """collects all the beams that intersect with the given line and returns the intersection points"""
        beams_to_intersect = []
        for val in slab_populator.edge_beams.values():
            beams_to_intersect.extend(val)
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        return intersection_line_beams(line, beams_to_intersect, max_distance=beam_dimensions["stud"][0])

    def _create_studs_from_intersections(self, intersections, slab_populator, min_length=TOL.absolute):
        """parses the intersections and creates stud beams from them"""


        return studs

    @staticmethod
    def _create_plates(slab_populator):
        plates = []
        if slab_populator.detail_set.sheeting_inside:
            plates.append(Plate(slab_populator.outline_a, slab_populator.frame_outline_a))
        if slab_populator.detail_set.sheeting_outside:
            plates.append(Plate(slab_populator.outline_b, slab_populator.frame_outline_b))
        return plates


class SlabDetailA(SlabDetailBase):
    """A slab detail set that uses the default edge beams, studs, and plates."""

    BEAM_CATEGORY_NAMES = ["stud", "edge_stud", "top_plate_beam", "bottom_plate_beam"]
    RULES = [
        CategoryRule(TButtJoint, "stud", "top_plate_beam"),
        CategoryRule(LButtJoint, "edge_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "stud", "bottom_plate_beam"),
        CategoryRule(LButtJoint, "edge_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "stud", "edge_stud"),
        CategoryRule(TButtJoint, "stud", "detail"),
    ]

    def create_elements(self, slab_populator):
        """Generates the elements for the slab."""
        slab_populator.elements.extend(self._create_edge_beams(slab_populator))
        slab_populator.elements.extend(self._create_studs(slab_populator))
        slab_populator.elements.extend(self._create_plates(slab_populator))
        return slab_populator.elements

    def create_joints(self, slab_populator):
        """Generates the joints for the slab."""
        direct_rules = []
        direct_rules.extend(self._create_edge_joints(slab_populator))
        slab_populator.direct_rules.extend(direct_rules)
        return direct_rules


class SlabDetailB(SlabDetailBase):
    """A slab detail set that uses the edge beams and plates but no studs."""

    BEAM_CATEGORY_NAMES = ["stud", "edge_stud", "top_plate_beam", "bottom_plate_beam"]
    RULES = [
        CategoryRule(LButtJoint, "edge_stud", "top_plate_beam"),
        CategoryRule(LButtJoint, "edge_stud", "bottom_plate_beam"),
    ]

    def create_elements(self, slab_populator):
        """Generates the elements for the slab."""
        elements = []
        elements.extend(self._create_edge_beams(slab_populator))
        elements.extend(self._create_plates(slab_populator))
        slab_populator.elements.extend(elements)
        return elements

    def create_joints(self, slab_populator):
        """Generates the joints for the slab."""
        direct_rules=[]
        direct_rules.extend(self._create_edge_joints(slab_populator))
        slab_populator.direct_rules.extend(direct_rules)
        return direct_rules
