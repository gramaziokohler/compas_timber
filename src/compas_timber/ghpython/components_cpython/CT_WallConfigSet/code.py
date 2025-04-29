# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System

from compas_timber.connections import JointTopology
from compas_timber.design import LConnectionDetailA
from compas_timber.design import TConnectionDetailA
from compas_timber.design import WallPopulatorConfigurationSet
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class WallPopulatorConfigSetComponent(Grasshopper.Kernel.GH_ScriptInstance):
    DEFAULT_DETAILS = {JointTopology.TOPO_L: LConnectionDetailA(), JointTopology.TOPO_T: TConnectionDetailA()}

    def RunScript(
        self,
        stud_spacing: float,
        beam_width: float,
        sheeting_outside: float,
        sheeting_inside: float,
        lintel_posts: bool,
        edge_stud_offset: float,
        custom_dimensions: System.Collections.Generic.List[object],
        joint_overrides: System.Collections.Generic.List[object],
    ):
        if not item_input_valid_cpython(ghenv, stud_spacing, "Stud Spacing") or not item_input_valid_cpython(ghenv, beam_width, "Beam Width"):
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
