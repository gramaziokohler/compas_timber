from .joint import JointTopology
from .plate_butt_joint import PlateButtJoint, PlateLButtJoint, PlateTButtJoint
from .slab_joint import SlabJoint


class SlabButtJoint(SlabJoint, PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def __data__(self):
        data = super(SlabButtJoint, self).__data__
        data["main_slab_guid"] = self._main_slab_guid
        data["cross_slab_guid"] = self._cross_slab_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, main_slab, cross_slab, topology, main_segment_index, cross_segment_index, **kwargs):
        super(SlabButtJoint, self).__init__(main_slab, cross_slab, topology, main_segment_index, cross_segment_index, **kwargs)

    @property
    def main_slab(self):
        """Return the main slab."""
        return self.plate_a

    @property
    def cross_slab(self):
        """Return the cross slab."""
        return self.plate_b

    @property
    def _main_slab_guid(self):
        """Return the GUID of the main slab."""
        return self.plate_a.guid if self.plate_a else None

    @property
    def _cross_slab_guid(self):
        """Return the GUID of the cross slab."""
        return self.plate_b.guid if self.plate_b else None

    def __repr__(self):
        return "SlabButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))


class SlabLButtJoint(SlabButtJoint, PlateLButtJoint):
    """Creates a plate-to-plate butt-joint connection."""
    @property
    def __data__(self):
        data = super(SlabLButtJoint, self).__data__
        data["main_slab_guid"] = self._main_slab_guid
        data["cross_slab_guid"] = self._cross_slab_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, main_slab, cross_slab, topology, main_segment_index, cross_segment_index, details=None, **kwargs):
        super(SlabLButtJoint, self).__init__(main_slab, cross_slab, topology, main_segment_index, cross_segment_index, **kwargs)
        self.details = details

    def __repr__(self):
        return "SlabLButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))


class SlabTButtJoint(SlabButtJoint,  PlateTButtJoint):
    """Creates a plate-to-plate butt-joint connection."""
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(SlabTButtJoint, self).__data__
        data["main_slab_guid"] = self._main_slab_guid
        data["cross_slab_guid"] = self._cross_slab_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        return data

    def __init__(self, main_slab, cross_slab, topology, main_segment_index, **kwargs):
        super(SlabTButtJoint, self).__init__(main_slab, cross_slab, topology, main_segment_index, **kwargs)

    def __repr__(self):
        return "SlabTButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))
