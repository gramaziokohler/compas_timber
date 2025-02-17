from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import JointTopology
from compas_timber.design import LConnectionDetailA
from compas_timber.design import TConnectionDetailA
from compas_timber.design import WallPopulatorConfigurationSet


class WallPopulatorConfigSetComponent(component):
    DEFAULT_DETAILS = {JointTopology.TOPO_L: LConnectionDetailA(), JointTopology.TOPO_T: TConnectionDetailA()}

    def RunScript(self, stud_spacing, beam_width, sheeting_outside, sheeting_inside, lintel_posts, edge_stud_offset, custom_dimensions, joint_overrides):
        if not stud_spacing:
            self.AddRuntimeMessage(Warning, "Input parameter 'Stud Spacing' failed to collect data")
        if not beam_width:
            self.AddRuntimeMessage(Warning, "Input parameter 'Beam Width' failed to collect data")

        if not (stud_spacing and beam_width):
            return

        dims = {}
        for item in custom_dimensions:
            for key, val in item.items():
                dims[key] = val

        config_set = WallPopulatorConfigurationSet.default(stud_spacing, beam_width)
        config_set.connection_details = self.DEFAULT_DETAILS

        if dims is not None:
            config_set.custom_dimensions = dims
        if sheeting_inside is not None:
            config_set.sheeting_inside = sheeting_inside
        if sheeting_outside is not None:
            config_set.sheeting_outside = sheeting_outside
        if lintel_posts is not None:
            config_set.lintel_posts = lintel_posts
        if edge_stud_offset is not None:
            config_set.edge_stud_offset = edge_stud_offset
        if joint_overrides is not None:
            config_set.joint_overrides = joint_overrides
        return config_set
