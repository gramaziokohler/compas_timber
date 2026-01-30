from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateButtJoint(PlateJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def main_plate(self):
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_plate(self):
        """Return the cross plate."""
        return self.plate_b

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
    def _main_planes(self):
        """Return the ordered planes of the main plate."""
        return self.a_planes

    @property
    def _cross_planes(self):
        """Return the ordered planes of the cross plate."""
        return self.b_planes

    def __repr__(self):
        return "PlateButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))


class PlateLButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    def __repr__(self):
        return "PlateLButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _set_edge_planes(self):
        self.main_plate.set_extension_plane(self.main_segment_index, self._cross_planes[0])
        self.cross_plate.set_extension_plane(self.cross_segment_index, self._main_planes[1])


class PlateTButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_FACE

    def __repr__(self):
        return "PlateTButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _set_edge_planes(self):
        self.main_plate.set_extension_plane(self.main_segment_index, self._cross_planes[0])
