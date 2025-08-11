# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System
import rhinoscriptsyntax as rs

from compas.geometry import intersection_segment_segment
from compas_rhino.conversions import polyline_to_compas

from compas_timber.connections import JointTopology
from compas_timber.design import LConnectionDetailA
from compas_timber.design import TConnectionDetailA
from compas_timber.elements import Opening
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython
from compas_timber.design.opening_details import WindowDetailA, WindowDetailB


class WindowComponent(Grasshopper.Kernel.GH_ScriptInstance):
    DEFAULT_DETAILS = {JointTopology.TOPO_L: LConnectionDetailA(), JointTopology.TOPO_T: TConnectionDetailA()}

    def RunScript(
        self,
        outline,
        lintel_posts: bool,
        custom_dimensions: System.Collections.Generic.List[object],
        joint_overrides: System.Collections.Generic.List[object],
    ):
        """default values for stud spacing and beam width"""
        if not item_input_valid_cpython(ghenv, outline, "Outline"):
            return
        dims = {}
        for item in custom_dimensions:
            for key, val in item.items():
                dims[key] = val

        _, o_geometry = self._get_guid_and_geometry(outline)
        o_rhino_polyline = rs.coercecurve(o_geometry)
        compas_outline = polyline_to_compas(o_rhino_polyline.ToPolyline())

        if not lintel_posts:
            detail_set = WindowDetailA(dimension_overrides=dims, joint_overrides=joint_overrides)
        else:
            detail_set = WindowDetailB(dimension_overrides=dims, joint_overrides=joint_overrides)

        return Opening(outline=compas_outline, detail_set=detail_set)
