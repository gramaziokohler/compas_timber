import math

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import intersection_segment_segment

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.design import DirectRule
from compas_timber.design.details import DetailBase
from compas_timber.elements import Beam, slab
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import split_beam_at_lengths


class InterfaceDetailBase(DetailBase):
    """Base class for interface detail sets."""

    BEAM_CATEGORY_NAMES = ["detail"]

    RULES = [
        CategoryRule(TButtJoint, "detail", "edge_stud"),
        CategoryRule(TButtJoint, "detail", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "detail", "top_plate_beam"),
        CategoryRule(TButtJoint, "detail", "edge_stud"),
        CategoryRule(TButtJoint, "king_stud", "detail"),
        CategoryRule(TButtJoint, "jack_stud", "detail"),
        CategoryRule(TButtJoint, "stud", "detail"),
    ]

    def __init__(self, beam_width_overrides=None, joint_rule_overrides=None):
        super(InterfaceDetailBase, self).__init__(beam_width_overrides, joint_rule_overrides)

    def update_rules(self, joint_rule_overrides):
        """Update the rules with any overrides provided."""
        rules = [r for r in self.RULES]
        for override in joint_rule_overrides:
            for rule in rules:
                if override.category_a == rule.category_a and override.category_b == rule.category_b:
                    rule = override
                    break
            else:
                rules.append(override)
        return rules

    def cull_and_split_studs(self, interface, slab_populator, min_length=None):
        """Split studs with an interface."""
        return

    def create_elements(self, interface, slab_populator):
        """Generate the beams for the interface."""
        elements=[]
        if interface.interface_role == "CROSS":
            elements.extend(self._create_elements_cross(interface, slab_populator))
        elif interface.interface_role == "MAIN":
            elements.extend(self._create_elements_main(interface, slab_populator))
        elif interface.interface_role == "NONE":
            elements.extend(self._create_elements_none(interface, slab_populator))
        slab_populator.elements.extend(elements)
        return elements

    def create_joints(self, interface, slab_populator):
        """Generate the joints for the interface."""
        direct_rules = []
        if interface.interface_role == "CROSS":
            direct_rules.extend(self._create_joints_cross(interface, slab_populator))
        elif interface.interface_role == "MAIN":
            direct_rules.extend(self._create_joints_main(interface, slab_populator))
        elif interface.interface_role == "NONE":
            direct_rules.extend(self._create_joints_none(interface, slab_populator))
        slab_populator.direct_rules.extend(direct_rules)
        return direct_rules

    def _create_elements_main(self, interface, slab_populator):
        """Generate the beams for a main interface."""
        raise NotImplementedError("create_elements_main must be implemented in subclasses.")

    def _create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a cross interface."""
        raise NotImplementedError("create_elements_cross must be implemented in subclasses.")

    def _create_elements_none(self, interface, slab_populator):
        """Generate the beams for a none interface."""
        raise NotImplementedError("create_elements_none must be implemented in subclasses.")


class LDetailBase(InterfaceDetailBase):
    """Base class for L-butt detail sets."""

    def _create_elements_main(self, interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.extend(slab_populator.edge_beams[interface.edge_index])
        return []

    def _create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a cross interface."""
        interface.beams.extend(slab_populator.edge_beams[interface.edge_index])
        return []

    def _create_elements_none(self, interface, slab_populator):
        """Generate the beams for a none interface."""
        interface.beams.extend(slab_populator.edge_beams[interface.edge_index])
        return []


class TDetailBase(InterfaceDetailBase):
    """Base class for T-butt detail sets."""
    def _create_elements_main(self, interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.extend(slab_populator.edge_beams[interface.edge_index])
        return []

    def _create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a cross interface."""
        return []

    def _create_elements_none(self, interface, slab_populator):
        """Generate the beams for a none interface."""
        raise ValueError("TDetailBase does not support NONE interfaces. Must be MAIN or CROSS interface role.")

    def _create_joints_cross(self, interface, slab_populator):
        """Generate the joints for a cross interface."""
        return []

    def _create_joints_main(self, interface, slab_populator):
        """Generate the joints for a main interface."""
        return []

    def _create_joints_none(self, interface, slab_populator):
        """Generate the joints for a none interface."""
        return []


class LButtDetailB(LDetailBase):
    """Detail Set that creates the beams for a L-butt a 3-beam box in the Cross Slab."""

    def _create_elements_main(self, interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.extend(slab_populator.edge_beams[interface.edge_index])
        return []

    def _create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a L-cross interface."""
        beam_dimensions = DetailBase.get_beam_dimensions(self, slab_populator)
        edge_beam = slab_populator.edge_beams[interface.edge_index][0]
        edge = edge_beam.centerline
        stud_width = beam_dimensions["detail"][0]
        stud_height = beam_dimensions["detail"][1]
        flat_line = edge.translated(interface.frame.yaxis * (edge_beam.width + stud_height) * 0.5)
        inner_line = flat_line.translated(interface.frame.yaxis * (stud_width + stud_height) * 0.5)
        flat_line.translate(interface.frame.zaxis * (stud_width - edge_beam.height) * 0.5)
        edge.translate(interface.frame.yaxis * stud_height * 0.5)
        flat_beam = Beam.from_centerline(flat_line, width=stud_height, height=stud_width, z_vector=slab_populator._slab.frame.normal)
        inner_beam = self.beam_from_category(inner_line, "detail", slab_populator, normal_offset=False)
        interface.beams = [edge_beam, flat_beam, inner_beam]
        return [flat_beam, inner_beam]

    def cull_and_split_studs(self, interface, slab_populator, min_length=None):
        """Split studs with an interface."""
        if interface.interface_role != "CROSS":
            return
        new_studs = []
        min_length = min_length or self.get_beam_dimensions(slab_populator)["detail"][0]
        int_beams = interface.beams
        studs=slab_populator.get_elements_by_category("stud")
        while studs:
            stud = studs.pop(0)
            slab_populator.elements.remove(stud)
            dots = []
            for int_beam in int_beams:
                intersection = intersection_segment_segment(stud.centerline, int_beam.centerline)[0]
                if not intersection:
                    continue
                dots.append(dot_vectors(stud.centerline.direction, Vector.from_start_end(stud.centerline.start, intersection)))
            stud_segs = split_beam_at_lengths(stud, dots)
            for seg in stud_segs:
                if not is_point_in_polyline(seg.midpoint, interface.beam_polyline, in_plane=False) and seg.length >= min_length:
                    new_studs.append(seg)
        slab_populator.elements.extend(new_studs)

    def _create_joints_main(self, interface, slab_populator):
        """Generate the joints for a main interface."""
        return []

    def _create_joints_cross(self, interface, slab_populator):
        """Generate the joints for a cross interface."""
        direct_rules = []
        self._create_joints_to_adjacent_edges(interface, slab_populator)

        return []


    def create_interface_interface_joints(self, interface_a, interface_b, slab_populator, interior_corner):
        """Generate the joints between beams of adjacent SlabLButtJoint interfaces."""
        if interface_a.detail_set is not interface_b.detail_set:
            raise ValueError("Cannot create joints between interfaces with different detail sets: {} and {}".format(interface_a.detail_set, interface_b.detail_set))
        edge_index = interface_b.edge_index
        interface_a_angle = angle_vectors(interface_a.frame.xaxis, slab_populator.stud_direction)
        interface_a_angle = min(interface_a_angle, math.pi - interface_a_angle)
        interface_b_angle = angle_vectors(interface_b.frame.xaxis, slab_populator.stud_direction)
        interface_b_angle = min(interface_b_angle, math.pi - interface_b_angle)
        direct_rules = []
        if interior_corner:
            if interface_a_angle < interface_b_angle:
                plane = Plane(slab_populator._slab.edge_planes[edge_index].point, -slab_populator._slab.edge_planes[edge_index].normal)  # a: main, b: cross
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[0], interface_b.beams[0]], butt_plane=plane))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[1], interface_b.beams[0]], butt_plane=plane))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[0], interface_a.beams[2]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[1], interface_a.beams[2]]))
                direct_rules.append(DirectRule(LButtJoint, [interface_b.beams[2], interface_a.beams[2]]))
            else:
                plane = Plane(slab_populator._slab.edge_planes[edge_index - 1].point, -slab_populator._slab.edge_planes[edge_index - 1].normal)  # b: main, a: cross
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[0], interface_a.beams[0]], butt_plane=plane))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[1], interface_a.beams[0]], butt_plane=plane))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[0], interface_b.beams[2]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[1], interface_b.beams[2]]))
                direct_rules.append(DirectRule(LButtJoint, [interface_a.beams[2], interface_b.beams[2]]))
        else:
            if interface_a_angle < interface_b_angle:
                direct_rules.append(DirectRule(LButtJoint, [interface_b.beams[0], interface_a.beams[0]], back_plane=slab_populator.edge_planes[edge_index]))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[1], interface_a.beams[0]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[2], interface_a.beams[0]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[1], interface_b.beams[2]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[2], interface_b.beams[2]]))

            else:
                direct_rules.append(DirectRule(LButtJoint, [interface_a.beams[0], interface_b.beams[0]], back_plane=slab_populator._slab.edge_planes[edge_index - 1]))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[1], interface_b.beams[0]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_a.beams[2], interface_b.beams[0]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[1], interface_a.beams[2]]))
                direct_rules.append(DirectRule(TButtJoint, [interface_b.beams[2], interface_a.beams[2]]))
        return direct_rules

    @staticmethod
    def create_interface_beam_joint(interface, beam, slab_populator, interior_corner):
        """Generate the joints between beams of a SlabLButtJoint with an adjacent edge beam."""
        beam_index = beam.attributes["edge_index"]
        interface_index = interface.edge_index
        direct_rules = []
        if interior_corner:
            plane = Plane(slab_populator._slab.edge_planes[beam_index].point, -slab_populator.edge_planes[beam_index].normal)
            direct_rules.append(DirectRule(TButtJoint, [interface.beams[0], beam], butt_plane=plane))
            direct_rules.append(DirectRule(TButtJoint, [interface.beams[1], beam], butt_plane=plane))
            direct_rules.append(DirectRule(LButtJoint, [interface.beams[2], beam], butt_plane=plane))
        else:
            direct_rules.append(DirectRule(LButtJoint, [interface.beams[0], beam], back_plane=slab_populator.edge_planes[interface_index]))
            direct_rules.append(DirectRule(TButtJoint, [interface.beams[1], beam]))
            direct_rules.append(DirectRule(TButtJoint, [interface.beams[2], beam]))
        return direct_rules

    def _extend_interface_beams(self, interface_a, interface_b):
        ip, ic = intersection_line_line(interface_a.beams[-1].centerline, interface_b.beams[-1].centerline)
        if ip and ic:
            # if the previous and current edge beams intersect, we extend the previous beam to the intersection point
            interface_a.beams[-1].length = interface_a.beams[-1].frame.point.distance_to_point(ip)
            interface_b.beams[-1].length = interface_b.beams[-1].centerline.end.distance_to_point(ic)
            interface_b.beams[-1].frame.point = ic



class TButtDetailB(TDetailBase):
    """Detail Set that creates the beams for a T-butt a 3-beam box in the Cross Slab."""

    def _create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a T-cross interface."""
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        edge = interface.polyline.lines[0]
        edge.translate(interface.frame.yaxis * interface.width * 0.5)
        width = beam_dimensions["detail"][0]
        height = beam_dimensions["detail"][1]
        if dot_vectors(interface.frame.normal, slab_populator.normal) < 0:
            offset = slab_populator.detail_set.sheeting_outside
        else:
            offset = slab_populator.detail_set.sheeting_inside

        flat_beam = Beam.from_centerline(edge, width=height, height=width, z_vector=slab_populator._slab.frame.normal)
        flat_beam.frame.translate(interface.frame.zaxis * (flat_beam.height * 0.5 + offset))
        stud_edge_a = edge.translated(interface.frame.yaxis * (width + height) * 0.5)
        stud_edge_b = edge.translated(-interface.frame.yaxis * (width + height) * 0.5)

        beam_a = self.beam_from_category(stud_edge_a, "detail", slab_populator, normal_offset=False)
        beam_a.frame.translate(interface.frame.normal * (beam_a.height * 0.5 + offset))
        beam_b = self.beam_from_category(stud_edge_b, "detail", slab_populator, normal_offset=False)
        beam_b.frame.translate(interface.frame.normal * (beam_b.height * 0.5 + offset))
        interface.beams = [beam_a, flat_beam, beam_b]

        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        return interface.beams

    def cull_and_split_studs(self, interface, slab_populator, min_length=None):
        """Split studs with an interface."""
        if interface.interface_role != "CROSS":
            return
        new_studs = []
        min_length = min_length or self.get_beam_dimensions(slab_populator)["detail"][0]
        int_beams = interface.beams
        studs = slab_populator.get_elements_by_category("stud")
        while studs:
            stud = studs.pop(0)
            slab_populator.elements.remove(stud)
            dots = []
            for int_beam in int_beams:
                intersection = intersection_segment_segment(stud.centerline, int_beam.centerline)[0]
                if not intersection:
                    continue
                dots.append(dot_vectors(stud.centerline.direction, Vector.from_start_end(stud.centerline.start, intersection)))
            stud_segs = split_beam_at_lengths(stud, dots)
            for seg in stud_segs:
                if not is_point_in_polyline(seg.midpoint, interface.beam_polyline, in_plane=False) and seg.length >= min_length:
                    new_studs.append(seg)
        slab_populator.elements.extend(new_studs)

    def _create_joints_cross(self, interface, slab_populator):
        """Generate the joints between T-BUTT interfaces and slab edge beams."""
        joints = []
        for beam in interface.beams:
            pts = {}
            for i, seg in enumerate(slab_populator.frame_outline_a.lines):
                pt = intersection_line_segment(beam.centerline, seg)[0]
                if pt:
                    pts[i] = pt
            if len(pts.values()) != 2:
                raise ValueError("Could not find intersection points between beam {} and outline segments: {}".format(beam, pts))
            else:
                for i in pts.keys():
                    if slab_populator.edge_interfaces.get(i, None) and len(slab_populator.edge_interfaces[i].beams) > 0:
                        # if there is an interface with beams, we use the last interface beam to create the joint definition
                        joints.append(TButtJoint(beam, slab_populator.edge_interfaces[i].beams[-1]))
                    else:
                        # if there is no interface, we create a joint definition between the edge beam and the beam
                        for edge_beam in slab_populator.edge_beams[i]:
                            if intersection_line_segment(beam.centerline, edge_beam.centerline)[0]:
                                joints.append(DetailBase.get_joint_from_elements(beam, edge_beam))

        return joints

    @staticmethod
    def create_interface_beam_joint(interface, beam, slab_populator, interior_corner):
        """Generate the joints between beams of a SlabLButtJoint with an adjacent edge beam."""
        joints = []
        for int_beam in interface.beams:
            joints.append(TButtJoint(int_beam, beam))
        return joints

    def create_interface_interface_joints(self, interface_main, interface_cross, slab_populator, interior_corner):
        """Generate the joints between T_TOPO interfaces."""
        # NOTE: untested
        joints = []
        midpoint = Point(0,0,0)
        for pt in interface_main.polyline.points[:-1]:
            midpoint += pt
        midpoint= midpoint / len(interface_main.polyline.points[:-1])
        cross_beam = min(interface_cross.beams, key=lambda b: b.midpoint.distance_to_point(midpoint))
        for beam in interface_main.beams:
            joints.append(TButtJoint(beam, cross_beam))
        return joints
