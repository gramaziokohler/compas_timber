from .joint import JointTopology
from .plate_miter_joint import PlateMiterJoint


class SlabMiterJoint(PlateMiterJoint):
    """Creates a mitered edge plate-to-plate connection."""

    def __repr__(self):
        return "PlateMiterJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))


