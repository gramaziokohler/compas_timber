from .joint import JointTopology
from .slab_joint import SlabJoint
from .plate_butt_joint import PlateButtJoint
from .plate_butt_joint import PlateLButtJoint
from .plate_butt_joint import PlateTButtJoint


class SlabButtJoint(SlabJoint, PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def main_slab(self):
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_slab(self):
        """Return the cross plate."""
        return self.plate_b

    def __repr__(self):
        return "SlabButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))


class SlabLButtJoint(SlabButtJoint, PlateLButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    def __repr__(self):
        return "SlabLButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))


class SlabTButtJoint(SlabButtJoint, PlateTButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    def __repr__(self):
        return "SlabTButtJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))

