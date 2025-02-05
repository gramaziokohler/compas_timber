from compas.geometry import Box
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import intersection_line_plane

from compas_timber.connections import InterfaceLocation

from .wall_populator import BeamDefinition


class LDetailBase(object):
    def adjust_segments_main(self, interface, wall, config_set, perimeter_segments):
        # top and bottom segments are shortened/extended to the intersection plane
        # front or back (depending on the end at which the deailt is) segment are moved to the end of the interface
        # shorten top and bottom segments to the interface
        interface_plane = Plane.from_three_points(*interface.interface_polyline.points[:3])  # TODO: Interface.as_plane()
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
        # top and bottom are extended to meet the other end of the main wall
        # front or back (depending on the end at which the deailt is) segment are moved to the end of the interface
        outer_point = interface.interface_polyline[2]
        edge_plane = Plane(outer_point, wall.baseline.direction)
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
        interface_plane = Plane.from_three_points(*interface.interface_polyline.points[:3])  # TODO: Interface.as_plane()
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

    def get_detail_obb_main(self, interface, config_set):
        xsize = config_set.beam_width  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set):
        xsize = config_set.wall_depth
        ysize = interface.interface_polyline.lines[0].length
        zsize = config_set.beam_width + config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        # TODO: this isn't quite right, fix
        # box_frame.point += interface.frame.zaxis * interface.interface_polyline.lines[1].length * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        left_vertical = interface.interface_polyline.lines[0]
        right_vertical = interface.interface_polyline.lines[2]
        parallel_to_interface = interface.frame.normal
        perpendicular_to_interface = interface.frame.xaxis

        edge_beam_line = right_vertical.translated(parallel_to_interface * config_set.beam_width * -0.5)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, config_set.wall_depth, normal=perpendicular_to_interface)

        reference_edge = left_vertical.translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        between_edge = reference_edge.translated(interface.frame.normal * -1.0 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, config_set.wall_depth, normal=parallel_to_interface)
        return [between_beam, edge_beam]

    def create_elements_main(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, config_set.wall_depth, normal=beam_zaxis)
        return [edge_beam]


class LConnectionDetailA(LDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

    def get_detail_obb_main(self, interface, config_set):
        xsize = config_set.beam_width  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set):
        xsize = config_set.wall_depth
        ysize = interface.interface_polyline.lines[0].length
        zsize = 2 * config_set.beam_width + config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        # TODO: this isn't quite right, fix
        # box_frame.point += interface.frame.zaxis * interface.interface_polyline.lines[1].length * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        left_vertical = interface.interface_polyline.lines[0]
        right_vertical = interface.interface_polyline.lines[2]
        parallel_to_interface = interface.frame.normal
        perpendicular_to_interface = interface.frame.xaxis

        edge_beam_line = right_vertical.translated(parallel_to_interface * config_set.beam_width * -0.5)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, config_set.wall_depth, normal=perpendicular_to_interface)

        other_edge_line = edge_beam_line.translated(parallel_to_interface * -1.0 * (config_set.wall_depth + config_set.beam_width))
        other_edge = BeamDefinition(other_edge_line, config_set.beam_width, config_set.wall_depth, normal=perpendicular_to_interface)

        reference_edge = left_vertical.translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        between_edge = reference_edge.translated(interface.frame.normal * -1.0 * config_set.beam_width)
        between_beam = BeamDefinition(between_edge, config_set.beam_width, config_set.wall_depth, normal=parallel_to_interface)
        return [between_beam, edge_beam, other_edge]

    def create_elements_main(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, config_set.wall_depth, normal=beam_zaxis)
        return [edge_beam]


class TConnectionDetailA(TDetailBase):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

    def get_detail_obb_main(self, interface, config_set):
        xsize = config_set.beam_width  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def get_detail_obb_cross(self, interface, config_set):
        xsize = config_set.wall_depth  # xsize
        ysize = interface.interface_polyline.lines[0].length
        zsize = config_set.wall_depth
        box_frame = interface.frame.copy()
        box_frame.point += interface.frame.xaxis * xsize * 0.5
        box_frame.point += interface.frame.yaxis * ysize * 0.5
        box_frame.point += interface.frame.zaxis * zsize * 0.5
        return Box(xsize, ysize, zsize, frame=box_frame)

    def create_elements_cross(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        right_vertical = interface.interface_polyline.lines[2]
        parallel_to_interface = interface.frame.normal
        perpendicular_to_interface = interface.frame.xaxis

        interface_width = interface.interface_polyline.lines[1].length
        edge_beam_line = right_vertical.translated(parallel_to_interface * interface_width * -0.5)
        edge_beam = BeamDefinition(edge_beam_line, config_set.beam_width, config_set.wall_depth, normal=perpendicular_to_interface)

        return [edge_beam]

    def create_elements_main(self, interface, _, config_set):
        # create a beam (definition) as wide and as high as the wall
        # it should be flush agains the interface
        polyline = interface.interface_polyline
        beam_zaxis = interface.frame.normal
        reference_edge = polyline.lines[0].translated(interface.frame.xaxis * config_set.beam_width * 0.5)
        # TODO: if beam_height < wall thickness, there needs to be an offset here
        edge_beam = BeamDefinition(reference_edge, config_set.beam_width, config_set.wall_depth, normal=beam_zaxis)
        return [edge_beam]
