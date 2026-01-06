from .joint import JointTopology
from .panel_joint import PanelJoint
from .plate_miter_joint import PlateMiterJoint


class PanelMiterJoint(PanelJoint, PlateMiterJoint):
    """Creates a mitered edge plate-to-plate connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    def __repr__(self) -> str:
        return "PanelMiterJoint({0}, {1}, {2})".format(self.panel_a, self.panel_b, JointTopology.get_name(self.topology))
