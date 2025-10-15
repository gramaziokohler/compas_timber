from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateButtJoint(PlateJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def main_plate(self):
        """Return the main plate."""
        return self.plate_a

    @main_plate.setter
    def main_plate(self, value):
        """Set the main plate."""
        self.plate_a = value

    @property
    def cross_plate(self):
        """Return the cross plate."""
        return self.plate_b

    @cross_plate.setter
    def cross_plate(self, value):
        """Set the cross plate."""
        self.plate_b = value

    @property
    def main_segment_index(self):
        """Return the index of the segment in the main plate outline."""
        return self.a_segment_index

    @main_segment_index.setter
    def main_segment_index(self, value):
        """Set the index of the segment in the main plate outline."""
        self.a_segment_index = value

    @property
    def cross_segment_index(self):
        """Return the index of the segment in the cross plate outline."""
        return self.b_segment_index

    @cross_segment_index.setter
    def cross_segment_index(self, value):
        """Set the index of the segment in the cross plate outline."""
        self.b_segment_index = value

    @property
    def _main_plate_guid(self):
        """Return the GUID of the main plate."""
        return self.plate_a.guid if self.plate_a else None

    @property
    def _cross_plate_guid(self):
        """Return the GUID of the cross plate."""
        return self.plate_b.guid if self.plate_b else None

    @property
    def main_planes(self):
        """Return the ordered planes of the main plate."""
        return self.a_planes

    @property
    def cross_planes(self):
        """Return the ordered planes of the cross plate."""
        return self.b_planes

    @property
    def main_outlines(self):
        """Return the ordered outlines of the main plate."""
        return self.a_outlines

    @property
    def cross_outlines(self):
        """Return the ordered outlines of the cross plate."""
        return self.b_outlines

    def __repr__(self):
        return "PlateButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))



class PlateLButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    def __repr__(self):
        return "PlateLButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def set_edge_planes(self):
        self.main_plate.set_extension_plane(self.main_segment_index, self.cross_planes[0].transformed(self.main_plate.transformation_to_local()))
        self.cross_plate.set_extension_plane(self.cross_segment_index, self.main_planes[1].transformed(self.cross_plate.transformation_to_local()))

class PlateTButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_FACE

    def __repr__(self):
        return "PlateTButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))


    def set_edge_planes(self):
        self.main_plate.set_extension_plane(self.main_segment_index, self.cross_planes[0].transformed(self.main_plate.transformation_to_local()))
