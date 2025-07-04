from compas_timber.connections import InterfaceRole

from .joint import JointTopology
from .plate_joint import PlateJoint
from .plate_joint import move_polyline_segment_to_plane


class PlateButtJoint(PlateJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def __data__(self):
        data = super(PlateJoint, self).__data__
        data["main_plate_guid"] = self._main_plate_guid
        data["cross_plate_guid"] = self._cross_plate_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs):
        super(PlateButtJoint, self).__init__(main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs)

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

    @property
    def cross_segment_index(self):
        """Return the index of the segment in the main plate outline."""
        return self.b_segment_index

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

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.main_plate
        assert self.cross_plate

        for polyline in self.main_outlines:
            move_polyline_segment_to_plane(polyline, self.main_segment_index, self.cross_planes[0])

        if self.topology == JointTopology.TOPO_L:
            for polyline in self.cross_outlines:
                move_polyline_segment_to_plane(polyline, self.cross_segment_index, self.main_planes[1])

    @property
    def interface_main(self):
        return self.interface_a

    @property
    def interface_cross(self):
        return self.interface_a

    @property
    def interface_a(self):
        self._plate_a_interface = super(PlateButtJoint, self).interface_a
        self._plate_a_interface.interface_role = InterfaceRole.MAIN
        return self._plate_a_interface

    @property
    def interface_b(self):
        self._plate_b_interface = super(PlateButtJoint, self).interface_b
        self._plate_b_interface.interface_role = InterfaceRole.CROSS
        return self._plate_b_interface


class PlateLButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(PlateLButtJoint, self).__data__
        data["main_plate_guid"] = self._main_plate_guid
        data["cross_plate_guid"] = self._cross_plate_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs):
        super(PlateLButtJoint, self).__init__(main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs)

    def __repr__(self):
        return "PlateLButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.main_plate
        assert self.cross_plate

        for polyline in self.main_outlines:
            move_polyline_segment_to_plane(polyline, self.main_segment_index, self.cross_planes[0])

        for polyline in self.cross_outlines:
            move_polyline_segment_to_plane(polyline, self.cross_segment_index, self.main_planes[1])


class PlateTButtJoint(PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(PlateTButtJoint, self).__data__
        data["main_plate_guid"] = self._main_plate_guid
        data["cross_plate_guid"] = self._cross_plate_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        return data

    def __init__(self, main_plate, cross_plate, topology, main_segment_index, **kwargs):
        super(PlateTButtJoint, self).__init__(main_plate, cross_plate, topology, main_segment_index, **kwargs)

    def __repr__(self):
        return "PlateTButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.main_plate
        assert self.cross_plate

        for polyline in self.main_outlines:
            move_polyline_segment_to_plane(polyline, self.main_segment_index, self.cross_planes[0])
