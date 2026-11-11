from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import intersection_plane_plane

from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateMiterJoint(PlateJoint):
    """Creates a mitered edge plate-to-plate connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    def __repr__(self):
        return "PlateMiterJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    def _set_edge_planes(self):
        line_a = intersection_plane_plane(self.a_planes[0], self.b_planes[0])
        line_b = intersection_plane_plane(self.a_planes[1], self.b_planes[1])
        if not (line_a and line_b):  # plates parallel
            edge_a = self.plate_a.outline_a.lines[self.a_segment_index]
            edge_b = self.plate_b.outline_a.lines[self.b_segment_index]
            if edge_a.direction.dot(edge_b.direction) < 0:  # align two edges
                edge_b.flip()
            # get mid-line between two edges
            mid_line = Line((edge_a[0] + edge_b[0]) / 2, (edge_a[1] + edge_b[1]) / 2)
            plane = Plane.from_three_points(mid_line[0], mid_line[1], mid_line[0] + self.plate_a.normal)
        else:
            plane = Plane.from_three_points(line_a[0], line_a[1], line_b[0])
        self.plate_a.set_extension_plane(self.a_segment_index, plane)
        self.plate_b.set_extension_plane(self.b_segment_index, plane)
