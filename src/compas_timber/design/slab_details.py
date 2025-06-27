import math

from compas.geometry import Box
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import angle_vectors

from compas_timber.connections import InterfaceLocation
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from .slab_populator import beam_from_category
from compas_timber.elements import Beam


def _get_furthest_line(lines, point):
    furthest_line = lines[0]  # just to not start with None but one line will always be the furthest
    max_distance = -float("inf")

    for line in lines:
        start_distance = distance_point_point(line.start, point)
        end_distance = distance_point_point(line.end, point)

        max_line_projection = max(start_distance, end_distance)
        if max_line_projection > max_distance:
            max_distance = max_line_projection
            furthest_line = line
    return furthest_line


class LDetailBase(object):
    def adjust_segments_main(self, interface, slab, config_set, perimeter_segments):
        # top and bottom segments are shortened/extended to the intersection plane
        # front or back (depending on the end at which the deailt is) segment are moved to the end of the interface
        # shorten top and bottom segments to the interface
        interface_plane = interface.as_plane()
        top_segment = perimeter_segments["top"]
        bottom_segment = perimeter_segments["bottom"]
        intersection_top = intersection_line_plane(top_segment, interface_plane)
        intersection_bottom = intersection_line_plane(bottom_segment, interface_plane)

        if interface.interface_type == InterfaceLocation.BACK:
            perimeter_segments["top"] = Line(top_segment.start, intersection_top)
            perimeter_segments["bottom"] = Line(intersection_bottom, bottom_segment.end)

        elif interface.interface_type == InterfaceLocation.FRONT:
            perimeter_segments["top"] = Line(intersection_top, top_segment.end)
            perimeter_segments["bottom"] = Line(bottom_segment.start, intersection_bottom)

    def adjust_segments_cross(self, interface, slab, config_set, perimeter_segments):
        distance_a = distance_point_point(interface.interface_polyline[1], slab.baseline.midpoint)
        distance_b = distance_point_point(interface.interface_polyline[2], slab.baseline.midpoint)
        if distance_a > distance_b:
            outer_point = interface.interface_polyline[1]
        else:
            outer_point = interface.interface_polyline[2]
        edge_plane = Plane(outer_point, slab.baseline.direction)  # TODO: using interface.frame.zaxis instead
        top_segment = perimeter_segments["top"]
        bottom_segment = perimeter_segments["bottom"]
        bottom_point = intersection_line_plane(bottom_segment, edge_plane)
        top_point = intersection_line_plane(top_segment, edge_plane)
        if interface.interface_type == InterfaceLocation.FRONT:
            bottom_segment = Line(bottom_segment.start, bottom_point)
            top_segment = Line(top_point, top_segment.end)
        elif interface.interface_type == InterfaceLocation.BACK:
            bottom_segment = Line(bottom_point, bottom_segment.end)
            top_segment = Line(top_segment.start, top_point)

        perimeter_segments["top"] = top_segment
        perimeter_segments["bottom"] = bottom_segment



class LButtDetailB(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    def get_detail_obb_main(self, interface, config_set, slab):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = slab.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, slab):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = slab.baseline.direction * -1.0
        else:
            parallel_to_interface = slab.baseline.direction
        xsize = slab.thickness
        ysize = interface.interface_polyline.lines[0].length
        zsize = 2 * config_set.beam_width + slab.thickness  # a bit bigger than needs to be
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += parallel_to_interface * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, slab, config_set):
        if interface.interface_type == InterfaceLocation.FRONT:
            left_vertical = interface.interface_polyline.lines[0]
            parallel_to_interface = slab.baseline.direction * -1.0
        else:
            left_vertical = interface.interface_polyline.lines[2]
            parallel_to_interface = slab.baseline.direction

        perpendicular_to_interface = interface.frame.xaxis

        edge_offset = config_set.beam_width * 0.5 + config_set.edge_stud_offset
        edge_beam_line = left_vertical.translated(parallel_to_interface * edge_offset)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, slab.thickness, normal=perpendicular_to_interface, type="detail_edge")

        between_edge = edge_beam_line.translated(perpendicular_to_interface * 0.5 * config_set.beam_width)
        between_edge.translate(parallel_to_interface * 0.5 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, slab.thickness, normal=parallel_to_interface, type="detail")
        return [between_beam, edge_beam]

    def create_elements_main(self, interface, slab, config_set):
        # create a beam (definition) as wide and as high as the slab
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, slab.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]


class LButtDetailA(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    def get_detail_obb_main(self, interface, config_set, slab):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = slab.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, slab):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = slab.baseline.direction * -1.0
        else:
            parallel_to_interface = slab.baseline.direction
        xsize = slab.thickness
        ysize = interface.interface_polyline.lines[0].length
        zsize = 3 * config_set.beam_width + slab.thickness  # a bit bigger than needs to be
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += parallel_to_interface * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, slab, config_set):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = slab.baseline.direction * -1.0  # this should always point from the slab outwards direction of the interface
        else:
            parallel_to_interface = slab.baseline.direction

        vertical_lines = [interface.interface_polyline.lines[0], interface.interface_polyline.lines[2]]
        edge_vertical = _get_furthest_line(vertical_lines, slab.baseline.midpoint)

        perpendicular_to_interface = interface.frame.xaxis

        edge_offset = config_set.beam_width * 0.5 + config_set.edge_stud_offset
        edge_beam_line = edge_vertical.translated(parallel_to_interface * edge_offset)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, slab.thickness, normal=perpendicular_to_interface, type="detail_edge")

        other_edge_line = edge_beam_line.translated(parallel_to_interface * 1.0 * (slab.thickness + config_set.beam_width))
        other_beam = BeamDefinition(other_edge_line, config_set.beam_width, slab.thickness, normal=perpendicular_to_interface, type="detail")

        between_edge = edge_beam_line.translated(perpendicular_to_interface * 0.5 * config_set.beam_width)
        between_edge.translate(parallel_to_interface * 0.5 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, slab.thickness, normal=parallel_to_interface, type="detail")
        return [between_beam, edge_beam, other_beam]

    def create_elements_main(self, interface, slab, config_set):
        # create a beam (definition) as wide and as high as the slab
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, slab.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]


class TButtDetailA(TDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    def get_detail_obb_main(self, interface, config_set, slab):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = slab.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, slab):
        xsize = slab.thickness  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = slab.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize * 1.5, frame=box_frame)

    def create_elements_cross(self, interface, slab, config_set):
        # create a beam (definition) as wide and as high as the slab
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        top_midpoint = polyline.lines[1].midpoint
        bottom_midpoint = polyline.lines[3].midpoint
        axis = Line(top_midpoint, bottom_midpoint)
        perpendicular_to_interface = interface.frame.xaxis
        edge_beam = BeamDefinition(axis, config_set.beam_width, slab.thickness, normal=perpendicular_to_interface, type="detail")

        return [edge_beam]

    def create_elements_main(self, interface, slab, config_set):
        # create a beam (definition) as wide and as high as the slab
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, slab.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]



class LButtDetailB(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    def create_elements_cross(self, interface, slab_populator):
        """Generate the beams for a T-cross interface."""
        edge_beam = slab_populator._edge_beams[interface.edge_index]
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
        slab_populator._beams.extend([flat_beam, inner_beam])

    def create_interface_interface_joints(self, slab_populator, interface_a, interface_b, interior_corner):
        """Generate the joints between individual beams of adjacent SlabLButtJoints."""

        edge_index = interface_b.edge_index
        interface_a_angle = angle_vectors(interface_a.frame.xaxis, slab_populator.stud_direction)
        interface_a_angle = min(interface_a_angle, math.pi - interface_a_angle)
        interface_b_angle = angle_vectors(interface_b.frame.xaxis, slab_populator.stud_direction)
        interface_b_angle = min(interface_b_angle, math.pi - interface_b_angle)
        joints = []
        if interior_corner:
            if interface_a_angle < interface_b_angle:
                plane = Plane(slab_populator._slab.edge_planes[edge_index].point, -self._slab.edge_planes[edge_index].normal)  # a: main, b: cross
                joints.append(TButtJoint(interface_a.beams[0], interface_b.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_b.beams[0], interface_a.beams[2]))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[2]))
                joints.append(LButtJoint(interface_b.beams[2], interface_a.beams[2]))
            else:
                plane = Plane(slab_populator._slab.edge_planes[edge_index - 1].point, -self._slab.edge_planes[edge_index - 1].normal)  # b: main, a: cross
                joints.append(TButtJoint(interface_b.beams[0], interface_a.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_b.beams[1], interface_a.beams[0], butt_plane=plane))
                joints.append(TButtJoint(interface_a.beams[0], interface_b.beams[2]))
                joints.append(TButtJoint(interface_a.beams[1], interface_b.beams[2]))
                joints.append(LButtJoint(interface_a.beams[2], interface_b.beams[2]))

            self._extend_interface_beams(interface_a, interface_b)
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

    def create_interface_beam_joint(self, interface, beam, slab_populator, interior_corner):
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
            plane = Plane(self._slab.edge_planes[interface_index].point, -slab_populator._slab.edge_planes[interface_index].normal)
            joints.append(LButtJoint(interface.beams[0], beam, back_plane=slab_populator._slab.edge_planes[interface_index]))
            joints.append(TButtJoint(interface.beams[1], beam))
            joints.append(TButtJoint(interface.beams[2], beam))

    def _extend_interface_beams(self, interface_a, interface_b):

            ip, ic = intersection_line_line(interface_a.beams[-1].centerline, interface_b.beams[-1].centerline)
            if ip and ic:
                # if the previous and current edge beams intersect, we extend the previous beam to the intersection point
                interface_a.beams[-1].length = interface_a.beams[-1].frame.point.distance_to_point(ip)
                interface_b.beams[-1].length = interface_b.beams[-1].centerline.end.distance_to_point(ic)
                interface_b.beams[-1].frame.point = ic


class TButtDetailB(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
    """

    def create_elements_cross(self, interface, slab_populator):

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
        slab_populator._beams.extend([beam_a, flat_beam, beam_b])

    def create_joints_cross(self, interface, slab_populator):
        """Generate the joints between T_TOPO interfaces and slab edge beams."""
        joints = []
        for beam in interface.beams:
            pts = {}
            for i, seg in enumerate(slab_populator.outline_a.lines):
                pt = intersection_line_segment(beam.centerline, seg)[0]
                if pt:
                    pts[i] = pt
            if len(pts.values()) != 2:
                raise ValueError("Could not find intersection points between beam {} and outline segments: {}".format(beam, pts))
            else:
                for i in pts.keys():
                    if self.edge_interfaces.get(i, None) and len(slab_populator.edge_interfaces[i].beams) > 0:
                        # if there is an interface with beams, we use the last interface beam to create the joint definition
                        joints.append(TButtJoint(beam, slab_populator.edge_interfaces[i].beams[-1]))
                    else:
                        # if there is no interface, we create a joint definition between the edge beam and the beam
                        joints.append(TButtJoint(beam, slab_populator._edge_beams[i]))
        return joints

    def create_interface_interface_joints(self, slab_populator, interface_main, interface_cross):
        """Generate the joints between T_TOPO interfaces."""
        #NOTE: untested
        joints = []
        cross_beam = min(sorted(interface_cross.beams, key=lambda b: b.midpoint.distance_to_point(sum(interface_main.polyline.points[:-1])/len(interface_main.polyline.points[:-1]))))[0]
        for beam in interface_main.beams:
            joints.append(TButtJoint(beam, cross_beam))
        return joints
