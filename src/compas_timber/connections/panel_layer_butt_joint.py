from compas_timber.elements import Panel

from .joint import JointTopology
from .panel_joint import PanelJoint
from .plate_butt_joint import PlateLButtJoint
from .plate_butt_joint import PlateTButtJoint
from .panel_butt_joint import PanelLButtJoint


class PanelLLayerButtJoint(PanelJoint, PlateLButtJoint):
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

    def add_extensions(self):
        if not (self.main_panel.interior_layer and
                self.main_panel.core_layer and
                self.main_panel.interior_layer and
                self.cross_panel.exterior_layer and
                self.cross_panel.core_layer and
                self.cross_panel.exterior_layer
                ):
            raise NotImplementedError("Extensions can only be added to joints between panels with interior, core, and exterior layers. Use method Panel.define_core_layer.")
        interior_butt = PanelLButtJoint(
            panel_a=self.cross_panel.interior_layer,
            panel_b=self.main_panel.interior_layer,
            topology=self.topology,
            a_segment_index=self.b_segment_index,
            b_segment_index=self.a_segment_index
        )
        core_butt = PanelLButtJoint(
            panel_a=self.main_panel.core_layer,
            panel_b=self.cross_panel.core_layer,
            topology=self.topology,
            a_segment_index=self.a_segment_index,
            b_segment_index=self.b_segment_index
        )
        exterior_butt = PanelLButtJoint(
            panel_a=self.cross_panel.exterior_layer,
            panel_b=self.main_panel.exterior_layer,
            topology=self.topology,
            a_segment_index=self.b_segment_index,
            b_segment_index=self.a_segment_index
        )
        for butt in [interior_butt, core_butt, exterior_butt]:
            butt.add_extensions()



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
