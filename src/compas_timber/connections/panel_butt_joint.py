from .joint import JointTopology
from .panel_joint import PanelJoint
from .plate_butt_joint import PlateButtJoint
from .plate_butt_joint import PlateLButtJoint
from .plate_butt_joint import PlateTButtJoint


class PanelButtJoint(PanelJoint, PlateButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def main_panel(self):
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_panel(self):
        """Return the cross plate."""
        return self.plate_b

    def __repr__(self):
        return "PanelButtJoint({0}, {1}, {2})".format(self.main_panel, self.cross_panel, JointTopology.get_name(self.topology))


class PanelLButtJoint(PanelButtJoint, PlateLButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    def __repr__(self):
        return "PanelLButtJoint({0}, {1}, {2})".format(self.main_panel, self.cross_panel, JointTopology.get_name(self.topology))


class PanelTButtJoint(PanelButtJoint, PlateTButtJoint):
    """Creates a plate-to-plate butt-joint connection."""

    def __repr__(self):
        return "PanelTButtJoint({0}, {1}, {2})".format(self.main_panel, self.cross_panel, JointTopology.get_name(self.topology))
