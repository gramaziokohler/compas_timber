from compas_timber.elements import Panel

from .joint import JointTopology
from .panel_joint import PanelJoint
from .plate_butt_joint import PlateLButtJoint
from .plate_butt_joint import PlateTButtJoint


class PanelLButtJoint(PanelJoint, PlateLButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_EDGE

    @property
    def main_panel(self) -> Panel:
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_panel(self) -> Panel:
        """Return the cross plate."""
        return self.plate_b

    def __repr__(self) -> str:
        return "PanelLButtJoint({0}, {1}, {2})".format(self.main_panel, self.cross_panel, JointTopology.get_name(self.topology))


class PanelTButtJoint(PanelJoint, PlateTButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_EDGE_FACE

    @property
    def main_panel(self) -> Panel:
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_panel(self) -> Panel:
        """Return the cross plate."""
        return self.plate_b

    def __repr__(self) -> str:
        return "PanelTButtJoint({0}, {1}, {2})".format(self.main_panel, self.cross_panel, JointTopology.get_name(self.topology))
