from .wall_populator import BeamDefinition


class LConnectionDetailB(object):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

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


class LConnectionDetailA(object):
    """
    Parameters
    ----------
    interface : :class:`compas_timber.connections.WallToWallInterface`
    """

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
