from .joint import JointTopology
from .plate_joint import PlateJoint
from .plate_joint import move_polyline_segment_to_plane


class PlateMiterJoint(PlateJoint):
    """Creates a mitered edge plate-to-plate connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    def __repr__(self):
        return "PlateMiterJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""
        assert self.plate_a
        assert self.plate_b

        for polyline, plane in zip(self.a_outlines, self.b_planes):
            move_polyline_segment_to_plane(polyline, self.a_segment_index, plane)

        for polyline, plane in zip(self.b_outlines, self.a_planes):
            move_polyline_segment_to_plane(polyline, self.b_segment_index, plane)
