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
from compas_timber.design.opening_details import WindowDetailA, WindowDetailB, DoorDetailAA, DoorDetailAB, DoorDetailBA, DoorDetailBB


class DoorComponent(Grasshopper.Kernel.GH_ScriptInstance):
    DEFAULT_DETAILS = {JointTopology.TOPO_L: LConnectionDetailA(), JointTopology.TOPO_T: TConnectionDetailA()}

    def RunScript(
        self,
        outline,
        lintel_posts: bool,
        split_bottom_plate: bool,
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

        if not split_bottom_plate:
            split_bottom_plate = True

        if not lintel_posts and not split_bottom_plate:
            detail_set = DoorDetailAA(dimension_overrides=dims, joint_overrides=joint_overrides)
        elif lintel_posts and not split_bottom_plate:
            detail_set = DoorDetailBA(dimension_overrides=dims, joint_overrides=joint_overrides)
        elif not lintel_posts and split_bottom_plate:
            detail_set = DoorDetailAB(dimension_overrides=dims, joint_overrides=joint_overrides)
        else:
            detail_set = DoorDetailBB(dimension_overrides=dims, joint_overrides=joint_overrides)

        return Opening(outline=compas_outline, detail_set=detail_set)
