import math

from compas.geometry import Plane
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import Vector
from compas.geometry import intersection_segment_segment

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.design.details import DetailBase
from compas_timber.elements import Beam
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import split_beam_at_lengths

from .slab_populator import beam_from_category

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

    @staticmethod
    def cull_and_split_studs(interface, slab_populator, min_length=None):
        """Split studs with an interface."""
        new_studs = []
        min_length = min_length or slab_populator.beam_dimensions["stud"][0]
        int_beams = interface.beams
        while slab_populator.studs:
            stud = slab_populator.studs.pop(0)
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
        slab_populator.studs = new_studs




    def create_elements_main(self,interface, slab_populator):
        """Generate the beams for a main interface."""
        raise NotImplementedError("create_elements_main must be implemented in subclasses.")


    def create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a cross interface."""
        raise NotImplementedError("create_elements_cross must be implemented in subclasses.")

    def create_elements_none(self, interface, slab_populator):
        """Generate the beams for a none interface."""
        raise NotImplementedError("create_elements_none must be implemented in subclasses.")



class LDetailBase(InterfaceDetailBase):
    """Base class for L-butt detail sets."""


    def create_elements_main(self,interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []


    def create_elements_cross(self,interface, slab_populator):
        """Generate the beams for a cross interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []


    def create_elements_none(self,interface, slab_populator):
        """Generate the beams for a none interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []



class TDetailBase(InterfaceDetailBase):
    """Base class for T-butt detail sets."""

    def create_elements_main(self, interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []

    def create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a cross interface."""
        return []

    def create_elements_none(self, interface, slab_populator):
        """Generate the beams for a none interface."""
        raise ValueError("TDetailBase does not support NONE interfaces. Must be MAIN or CROSS interface role.")


class LButtDetailB(LDetailBase):
    """Detail Set that generates the beams for a L-butt a 3-beam box in the Cross Slab."""

    def create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a L-cross interface."""
        beam_dimensions = DetailBase.get_beam_dimensions(self, slab_populator)
        edge_beam = slab_populator._edge_beams[interface.edge_index][0]
        edge = edge_beam.centerline
        stud_width = beam_dimensions["detail"][0]
        stud_height = beam_dimensions["detail"][1]
        flat_line = edge.translated(interface.frame.yaxis * (edge_beam.width + stud_height) * 0.5)
        inner_line = flat_line.translated(interface.frame.yaxis * (stud_width + stud_height) * 0.5)
        flat_line.translate(interface.frame.zaxis * (stud_width - edge_beam.height) * 0.5)
        edge.translate(interface.frame.yaxis * stud_height * 0.5)
        normal = slab_populator._slab.frame.normal
        flat_beam = Beam.from_centerline(flat_line, width=stud_height, height=stud_width, z_vector=normal)
        inner_beam = beam_from_category(inner_line, "detail", normal, beam_dimensions, normal_offset=False)
        interface.beams = [edge_beam, flat_beam, inner_beam]
        return [flat_beam, inner_beam]

    @staticmethod
    def create_interface_interface_joints(interface_a, interface_b, slab_populator, interior_corner):
        """Generate the joints between beams of adjacent SlabLButtJoint interfaces."""
        if interface_a.detail_set is not interface_b.detail_set:
            raise ValueError("Cannot create joints between interfaces with different detail sets: {} and {}".format(interface_a.detail_set, interface_b.detail_set))
        edge_index = interface_b.edge_index
        interface_a_angle = angle_vectors(interface_a.frame.xaxis, slab_populator.stud_direction)
        interface_a_angle = min(interface_a_angle, math.pi - interface_a_angle)
        interface_b_angle = angle_vectors(interface_b.frame.xaxis, slab_populator.stud_direction)
        interface_b_angle = min(interface_b_angle, math.pi - interface_b_angle)
        joints = []
        if interior_corner:
            if interface_a_angle < interface_b_angle:
                plane = Plane(slab_populator._slab.edge_planes[edge_index].point, -slab_populator._slab.edge_planes[edge_index].normal)  # a: main, b: cross
                joints.append(TButtJoint(interface_a.beams[0], interface_b.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_b.beams[0], interface_a.beams[2]))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[2]))
                joints.append(LButtJoint(interface_b.beams[2], interface_a.beams[2]))
            else:
                plane = Plane(slab_populator._slab.edge_planes[edge_index - 1].point, -slab_populator._slab.edge_planes[edge_index - 1].normal)  # b: main, a: cross
                joints.append(TButtJoint(interface_b.beams[0], interface_a.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_a.beams[0], interface_b.beams[2]))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[2]))
                joints.append(LButtJoint(interface_a.beams[2], interface_b.beams[2]))
            # LButtDetailB._extend_interface_beams(interface_a, interface_b)
        else:
            if interface_a_angle < interface_b_angle:
                joints.append(LButtJoint(interface_b.beams[0], interface_a.beams[0], back_plane=slab_populator._slab.edge_planes[edge_index]))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[0]))
                joints.append(TButtJoint(interface_b.beams[2], interface_a.beams[0]))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[2]))
                joints.append(TButtJoint(interface_a.beams[2], interface_b.beams[2]))

            else:
                joints.append(LButtJoint(interface_a.beams[0], interface_b.beams[0], back_plane=slab_populator._slab.edge_planes[edge_index - 1]))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[0]))
                joints.append(TButtJoint(interface_a.beams[2], interface_b.beams[0]))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[2]))
                joints.append(TButtJoint(interface_b.beams[2], interface_a.beams[2]))
        return joints

    @staticmethod
    def create_interface_beam_joint(interface, beam, slab_populator, interior_corner):
        """Generate the joints between beams of a SlabLButtJoint with an adjacent edge beam."""
        beam_index = beam.attributes["edge_index"]
        interface_index = interface.edge_index
        joints = []
        if interior_corner:
            plane = Plane(slab_populator._slab.edge_planes[beam_index].point, -slab_populator._slab.edge_planes[beam_index].normal)
            joints.append(TButtJoint(interface.beams[0], beam, butt_plane=plane))
            joints.append(TButtJoint(interface.beams[1], beam, butt_plane=plane))
            joints.append(LButtJoint(interface.beams[2], beam, butt_plane=plane))
        else:
            plane = Plane(slab_populator._slab.edge_planes[interface_index].point, -slab_populator._slab.edge_planes[interface_index].normal)
            joints.append(LButtJoint(interface.beams[0], beam, back_plane=slab_populator._slab.edge_planes[interface_index]))
            joints.append(TButtJoint(interface.beams[1], beam))
            joints.append(TButtJoint(interface.beams[2], beam))
        return joints

    @staticmethod
    def _extend_interface_beams(interface_a, interface_b):
        ip, ic = intersection_line_line(interface_a.beams[-1].centerline, interface_b.beams[-1].centerline)
        if ip and ic:
            # if the previous and current edge beams intersect, we extend the previous beam to the intersection point
            interface_a.beams[-1].length = interface_a.beams[-1].frame.point.distance_to_point(ip)
            interface_b.beams[-1].length = interface_b.beams[-1].centerline.end.distance_to_point(ic)
            interface_b.beams[-1].frame.point = ic


class TButtDetailB(TDetailBase):
    """Detail Set that generates the beams for a T-butt a 3-beam box in the Cross Slab."""

    def create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a T-cross interface."""
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        edge = interface.polyline.lines[0]
        edge.translate(interface.frame.yaxis * interface.width * 0.5)
        width = beam_dimensions["detail"][0]
        height = beam_dimensions["detail"][1]
        if dot_vectors(interface.frame.normal, slab_populator._slab.frame.normal) < 0:
            offset = slab_populator._config_set.sheeting_outside
        else:
            offset = slab_populator._config_set.sheeting_inside

        flat_beam = Beam.from_centerline(edge, width=height, height=width, z_vector=slab_populator._slab.frame.normal)
        flat_beam.frame.translate(interface.frame.zaxis * (flat_beam.height * 0.5 + offset))
        stud_edge_a = edge.translated(interface.frame.yaxis * (width + height) * 0.5)
        stud_edge_b = edge.translated(-interface.frame.yaxis * (width + height) * 0.5)

        normal= slab_populator._slab.frame.normal
        beam_a = beam_from_category(stud_edge_a, "detail", normal, beam_dimensions, normal_offset=False)
        beam_a.frame.translate(interface.frame.normal * (beam_a.height * 0.5 + offset))
        beam_b = beam_from_category(stud_edge_b, "detail", normal, beam_dimensions, normal_offset=False)
        beam_b.frame.translate(interface.frame.normal * (beam_b.height * 0.5 + offset))
        interface.beams = [beam_a, flat_beam, beam_b]

        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        return interface.beams

    def create_joints_cross(self, interface, slab_populator):
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
                        for edge_beam in slab_populator._edge_beams[i]:
                            if intersection_line_segment(beam.centerline, edge_beam.centerline)[0]:
                                joints.append(get_joint_from_elements(beam, edge_beam))

        return joints

    @staticmethod
    def create_interface_interface_joints(interface_main, interface_cross):
        """Generate the joints between T_TOPO interfaces."""
        # NOTE: untested
        joints = []
        cross_beam = min(
            sorted(interface_cross.beams, key=lambda b: b.midpoint.distance_to_point(sum(interface_main.polyline.points[:-1]) / len(interface_main.polyline.points[:-1])))
        )[0]
        for beam in interface_main.beams:
            joints.append(TButtJoint(beam, cross_beam))
        return joints
