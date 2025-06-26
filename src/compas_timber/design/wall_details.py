from compas.geometry import Box
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane

from compas_timber.connections import InterfaceLocation

from .wall_populator import BeamDefinition


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
    def adjust_segments_main(self, interface, wall, config_set, perimeter_segments):
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

    def adjust_segments_cross(self, interface, wall, config_set, perimeter_segments):
        distance_a = distance_point_point(interface.interface_polyline[1], wall.baseline.midpoint)
        distance_b = distance_point_point(interface.interface_polyline[2], wall.baseline.midpoint)
        if distance_a > distance_b:
            outer_point = interface.interface_polyline[1]
        else:
            outer_point = interface.interface_polyline[2]
        edge_plane = Plane(outer_point, wall.baseline.direction)  # TODO: using interface.frame.zaxis instead
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


class TDetailBase(object):
    def adjust_segments_main(self, interface, wall, config_set, perimeter_segments):
        # top and bottom segments are shortened/extended to the intersection plane
        interface_plane = interface.as_plane()
        top_segment = perimeter_segments["top"]
        bottom_segment = perimeter_segments["bottom"]
        intersection_top = intersection_line_plane(top_segment, interface_plane)
        intersection_bottom = intersection_line_plane(bottom_segment, interface_plane)

        if interface.interface_type == InterfaceLocation.BACK:
            print("shortening top and bottom back")
            perimeter_segments["top"] = Line(top_segment.start, intersection_top)
            perimeter_segments["bottom"] = Line(intersection_bottom, bottom_segment.end)

        elif interface.interface_type == InterfaceLocation.FRONT:
            print("shortening top and bottom front")
            perimeter_segments["top"] = Line(intersection_top, top_segment.end)
            perimeter_segments["bottom"] = Line(bottom_segment.start, intersection_bottom)

    def adjust_segments_cross(self, *args, **kwargs):
        # top and bottom are not modified
        # internal segments are created on either side of the interface
        pass


class LConnectionDetailB(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

    def get_detail_obb_main(self, interface, config_set, wall):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = wall.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, wall):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = wall.baseline.direction * -1.0
        else:
            parallel_to_interface = wall.baseline.direction
        xsize = wall.thickness
        ysize = interface.interface_polyline.lines[0].length
        zsize = 2 * config_set.beam_width + wall.thickness  # a bit bigger than needs to be
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += parallel_to_interface * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, wall, config_set):
        if interface.interface_type == InterfaceLocation.FRONT:
            left_vertical = interface.interface_polyline.lines[0]
            parallel_to_interface = wall.baseline.direction * -1.0
        else:
            left_vertical = interface.interface_polyline.lines[2]
            parallel_to_interface = wall.baseline.direction

        perpendicular_to_interface = interface.frame.xaxis

        edge_offset = config_set.beam_width * 0.5 + config_set.edge_stud_offset
        edge_beam_line = left_vertical.translated(parallel_to_interface * edge_offset)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, wall.thickness, normal=perpendicular_to_interface, type="detail_edge")

        between_edge = edge_beam_line.translated(perpendicular_to_interface * 0.5 * config_set.beam_width)
        between_edge.translate(parallel_to_interface * 0.5 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, wall.thickness, normal=parallel_to_interface, type="detail")
        return [between_beam, edge_beam]

    def create_elements_main(self, interface, wall, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, wall.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]


class LConnectionDetailA(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

    def get_detail_obb_main(self, interface, config_set, wall):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = wall.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, wall):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = wall.baseline.direction * -1.0
        else:
            parallel_to_interface = wall.baseline.direction
        xsize = wall.thickness
        ysize = interface.interface_polyline.lines[0].length
        zsize = 3 * config_set.beam_width + wall.thickness  # a bit bigger than needs to be
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += parallel_to_interface * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, wall, config_set):
        if interface.interface_type == InterfaceLocation.FRONT:
            parallel_to_interface = wall.baseline.direction * -1.0  # this should always point from the wall outwards direction of the interface
        else:
            parallel_to_interface = wall.baseline.direction

        vertical_lines = [interface.interface_polyline.lines[0], interface.interface_polyline.lines[2]]
        edge_vertical = _get_furthest_line(vertical_lines, wall.baseline.midpoint)

        perpendicular_to_interface = interface.frame.xaxis

        edge_offset = config_set.beam_width * 0.5 + config_set.edge_stud_offset
        edge_beam_line = edge_vertical.translated(parallel_to_interface * edge_offset)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, wall.thickness, normal=perpendicular_to_interface, type="detail_edge")

        other_edge_line = edge_beam_line.translated(parallel_to_interface * 1.0 * (wall.thickness + config_set.beam_width))
        other_beam = BeamDefinition(other_edge_line, config_set.beam_width, wall.thickness, normal=perpendicular_to_interface, type="detail")

        between_edge = edge_beam_line.translated(perpendicular_to_interface * 0.5 * config_set.beam_width)
        between_edge.translate(parallel_to_interface * 0.5 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, wall.thickness, normal=parallel_to_interface, type="detail")
        return [between_beam, edge_beam, other_beam]

    def create_elements_main(self, interface, wall, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, wall.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]


class TConnectionDetailA(TDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

    def get_detail_obb_main(self, interface, config_set, wall):
        xsize = config_set.beam_width * 2.0  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = wall.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set, wall):
        xsize = wall.thickness  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = wall.thickness
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize * 1.5, frame=box_frame)

    def create_elements_cross(self, interface, wall, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        top_midpoint = polyline.lines[1].midpoint
        bottom_midpoint = polyline.lines[3].midpoint
        axis = Line(top_midpoint, bottom_midpoint)
        perpendicular_to_interface = interface.frame.xaxis
        edge_beam = BeamDefinition(axis, config_set.beam_width, wall.thickness, normal=perpendicular_to_interface, type="detail")

        return [edge_beam]

    def create_elements_main(self, interface, wall, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, wall.thickness, normal=beam_zaxis, type="detail_edge")
        return [edge_beam]
