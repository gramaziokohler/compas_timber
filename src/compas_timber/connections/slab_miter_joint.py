from .joint import JointTopology
from .plate_miter_joint import PlateMiterJoint
from .slab_joint import SlabJoint


class SlabMiterJoint(SlabJoint, PlateMiterJoint):
    """Creates a mitered edge plate-to-plate connection."""

    def __repr__(self):
        return "SlabMiterJoint({0}, {1}, {2})".format(self.slab_a, self.slab_b, JointTopology.get_name(self.topology))

