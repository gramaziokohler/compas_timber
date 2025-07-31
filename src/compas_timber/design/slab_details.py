import math

from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import dot_vectors
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.utils import distance_segment_segment

from .slab_populator import beam_from_category


class LDetailBase(object):
    """Base class for L-butt detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    @staticmethod
    def create_elements_main(interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []

    @staticmethod
    def create_elements_cross(interface, slab_populator):
        """Generate the beams for a cross interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []

    @staticmethod
    def create_elements_none(interface, slab_populator):
        """Generate the beams for a none interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []


class TDetailBase(object):
    """Base class for L-butt detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    @staticmethod
    def create_elements_main(interface, slab_populator):
        """Generate the beams for a main interface."""
        interface.beams.append(slab_populator._edge_beams[interface.edge_index][0])
        return []

    @staticmethod
    def create_elements_cross(interface, slab_populator):
        """Generate the beams for a cross interface."""
        return []

    @staticmethod
    def create_elements_none(interface, slab_populator):
        """Generate the beams for a none interface."""
        raise ValueError("TDetailBase does not support NONE interfaces. Must be MAIN or CROSS interface role.")


class LButtDetailB(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    @staticmethod
    def create_elements_cross(interface, slab_populator):
        """Generate the beams for a T-cross interface."""
        edge_beam = slab_populator._edge_beams[interface.edge_index][0]
        edge = edge_beam.centerline
        stud_width = slab_populator.beam_dimensions["stud"][0]
        stud_height = slab_populator.beam_dimensions["stud"][1]
        flat_line = edge.translated(interface.frame.yaxis * (edge_beam.width + stud_height) * 0.5)
        inner_line = flat_line.translated(interface.frame.yaxis * (stud_width + stud_height) * 0.5)
        flat_line.translate(interface.frame.zaxis * (stud_width - edge_beam.height) * 0.5)
        edge.translate(interface.frame.yaxis * stud_height * 0.5)
        flat_beam = Beam.from_centerline(flat_line, width=stud_height, height=stud_width, z_vector=slab_populator.normal)
        inner_beam = beam_from_category(slab_populator, inner_line, "stud", normal_offset=False)
        interface.beams = [edge_beam, flat_beam, inner_beam]
        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        return [flat_beam, inner_beam]

    @staticmethod
    def create_interface_interface_joints(interface_a, interface_b, slab_populator, interior_corner):
        """Generate the joints between individual beams of adjacent SlabLButtJoints."""
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
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    @staticmethod
    def create_elements_cross(interface, slab_populator):
        """Generate the beams for a T-cross interface."""
        edge = interface.polyline.lines[0]
        edge.translate(interface.frame.yaxis * interface.width * 0.5)
        stud_width = slab_populator.beam_dimensions["stud"][0]
        stud_height = slab_populator.beam_dimensions["stud"][1]
        flat_beam = Beam.from_centerline(edge, width=stud_height, height=stud_width, z_vector=slab_populator.normal)
        flat_beam.frame.translate(interface.frame.zaxis * flat_beam.height * 0.5)
        stud_edge_a = edge.translated(interface.frame.yaxis * (stud_width + stud_height) * 0.5)
        stud_edge_b = edge.translated(-interface.frame.yaxis * (stud_width + stud_height) * 0.5)
        beam_a = beam_from_category(slab_populator, stud_edge_a, "stud")
        beam_b = beam_from_category(slab_populator, stud_edge_b, "stud")
        interface.beams = [beam_a, flat_beam, beam_b]

        for beam in interface.beams:
            beam.attributes["category"] = "detail"
        return interface.beams

    @staticmethod
    def create_joints_cross(interface, slab_populator):
        """Generate the joints between T_TOPO interfaces and slab edge beams."""
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
                                joints.append(TButtJoint(beam, edge_beam))

        return joints

    @staticmethod
    def create_interface_interface_joints(interface_main, interface_cross, slab_populator):
        """Generate the joints between T_TOPO interfaces."""
        # NOTE: untested
        joints = []
        cross_beam = min(
            sorted(interface_cross.beams, key=lambda b: b.midpoint.distance_to_point(sum(interface_main.polyline.points[:-1]) / len(interface_main.polyline.points[:-1])))
        )[0]
        for beam in interface_main.beams:
            joints.append(TButtJoint(beam, cross_beam))
        return joints


