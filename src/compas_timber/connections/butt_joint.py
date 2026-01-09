from __future__ import annotations

import math
from ast import Return
from multiprocessing import Manager
from typing import TYPE_CHECKING
from typing import Optional
from unittest.main import main

from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import angle_vectors
from compas.geometry import centroid_points
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane_plane
from compas.geometry._core.centroids import midpoint_point_point
from compas.geometry.offset import intersect

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import Pocket
from compas_timber.fabrication.pocket import Polyhedron

from .joint import Joint
from .solver import JointTopology
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence

if TYPE_CHECKING:
    from compas_timber.elements.beam import Beam

class ButtJoint(Joint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam. This will be ignored if `butt_plane` is provided.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.


    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(ButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        data["modify_cross"] = self.modify_cross
        data["butt_plane"] = self.butt_plane
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self,
                main_beam: Beam = None,
                cross_beam: Beam = None,
                mill_depth: Optional[float] = None,
                modify_cross: bool = True,
                butt_plane: Optional[Plane] = None,
                force_pocket: bool = False,
                conical_tool: bool = False,
                **kwargs):
        super(ButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth = mill_depth or 0.0
        self.modify_cross = modify_cross
        self.butt_plane = butt_plane
        self.force_pocket = force_pocket
        self.conical_tool = conical_tool
        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

        return ref_side_index

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.
        """
        assert self.main_beam and self.cross_beam
        # extend the main beam
        try:
            if self.butt_plane:
                cutting_plane_main = self.butt_plane
                start_main, end_main = self.main_beam.extension_to_plane(cutting_plane_main)
                extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
                self.main_beam.add_blank_extension(
                    start_main + extension_tolerance,
                    end_main + extension_tolerance,
                    self.guid,
                )
            else:
                cutting_plane_main = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
                if self.mill_depth:
                    cutting_plane_main.translate(-cutting_plane_main.normal * self.mill_depth)
                start_main, end_main = self.main_beam.extension_to_plane(cutting_plane_main)

            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.main_beam.add_blank_extension(
                start_main + extension_tolerance,
                end_main + extension_tolerance,
                self.guid,
            )
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane_main])
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        # extend the cross beam
        if self.modify_cross:
            try:
                if self.back_plane:
                    cutting_plane_cross = self.back_plane
                else:
                    cutting_plane_cross = self.main_beam.opp_side(self.main_beam_ref_side_index)
                start_cross, end_cross = self.cross_beam.extension_to_plane(cutting_plane_cross)
            except AttributeError as ae:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane_cross])
            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.cross_beam.add_blank_extension(
                start_cross + extension_tolerance,
                end_cross + extension_tolerance,
                self.guid,
            )

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.
        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)
        # get the cutting plane for the main beam
        if self.butt_plane:
            cutting_plane = self.butt_plane
        else:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            cutting_plane.xaxis = -cutting_plane.xaxis
            if self.mill_depth:
                cutting_plane.translate(cutting_plane.normal * self.mill_depth)
        # apply the cut on the main beam
        main_feature = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.main_beam, self.main_beam_ref_side_index)
        self.main_beam.add_features(main_feature)
        # store the feature
        self.features = [main_feature]

        if self.force_pocket:
            self._apply_pocket_to_cross_beam()
        else:
            self._apply_lap_to_cross_beam()
        # apply a refinement cut on the cross beam
        if self.modify_cross:
            if self.back_plane:
                modification_plane = self.back_plane
            else:
                modification_plane = self.main_beam.opp_side(self.main_beam_ref_side_index)
            cross_refinement_feature = JackRafterCutProxy.from_plane_and_beam(modification_plane, self.cross_beam, self.cross_beam_ref_side_index)
            self.cross_beam.add_features(cross_refinement_feature)
            self.features.append(cross_refinement_feature)

    def _apply_lap_to_cross_beam(self):
        # apply the lap on the cross beam
        if self.mill_depth and not self.butt_plane:
            cross_cutting_plane = self.main_beam.ref_sides[self.main_beam_ref_side_index]
            lap_width = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[1]
            cross_feature = Lap.from_plane_and_beam(
                cross_cutting_plane,
                self.cross_beam,
                lap_width,
                self.mill_depth,
                ref_side_index=self.cross_beam_ref_side_index,
            )
            self.cross_beam.add_features(cross_feature)

            self.features.append(cross_feature)



    def _apply_pocket_to_cross_beam(self):


        cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        cutting_plane.xaxis = -cutting_plane.xaxis
        if self.mill_depth:
            cutting_plane.translate(cutting_plane.normal * self.mill_depth)


        main_beam_ref_sides = list(self.main_beam.ref_sides)

        plane_0 = Plane.from_frame(main_beam_ref_sides[0])
        plane_1 = Plane.from_frame(main_beam_ref_sides[1])
        plane_2 = Plane.from_frame(main_beam_ref_sides[2])
        plane_3 = Plane.from_frame(main_beam_ref_sides[3])
        cutting_plane = Plane.from_frame(cutting_plane)
        top_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index])
        vertices = [
            Point(*intersection_plane_plane_plane(plane_2, plane_3, cutting_plane)), #v0
            Point(*intersection_plane_plane_plane(plane_0, plane_3, cutting_plane)), #v1
            Point(*intersection_plane_plane_plane(plane_1, plane_0, cutting_plane)), #v2
            Point(*intersection_plane_plane_plane(plane_2, plane_1, cutting_plane)), #v3
            Point(*intersection_plane_plane_plane(plane_2, plane_3, top_plane)), #v4
            Point(*intersection_plane_plane_plane(plane_0, plane_3, top_plane)), #v5
            Point(*intersection_plane_plane_plane(plane_1, plane_0, top_plane)), #v6
            Point(*intersection_plane_plane_plane(plane_2, plane_1, top_plane)), #v7
        ]
        # faces = [
        #     [0, 1, 2, 3],
        #     [1, 5, 6, 2],
        #     [2, 6, 7, 3],
        #     [0, 3, 7, 4],
        #     [0, 4, 5, 1],
        #     [4, 7, 6, 5]
        # ]

        faces = [
            [0, 3, 2, 1],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [0, 4, 7, 3],
            [1, 5, 4, 0],
            [4, 5, 6, 7]
        ]

        print(self.cross_beam_ref_side_index)
        cutout_volume = Polyhedron(vertices, faces)
        pocket = Pocket.from_volume_and_element(cutout_volume, self.cross_beam, ref_side_index=self.cross_beam_ref_side_index)
        if not self.conical_tool:
            pocket.tilt_start_side = 90 if pocket.tilt_start_side < 90 else pocket.tilt_start_side
            pocket.tilt_end_side = 90 if pocket.tilt_end_side < 90 else pocket.tilt_end_side
            pocket.tilt_ref_side = 90 if pocket.tilt_ref_side < 90 else pocket.tilt_ref_side
            pocket.tilt_opp_side = 90 if pocket.tilt_opp_side < 90 else pocket.tilt_opp_side
        self.cross_beam.add_features(pocket)
        self.features.append(pocket)
        return cutout_volume






    # def _apply_pocket_to_cross_beam(self):
    #     int_point, _ = intersection_line_line(self.cross_beam.centerline, self.main_beam.centerline)
    #     angle, _ = self._compute_angle_and_dot_product(int_point)
    #     tilt_start_side = angle
    #     tilt_end_side = math.pi - angle
    #     start_x = self._find_start_x(int_point, angle)
    #     length = self._find_length(angle)
    #     width = self.main_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)[0]
    #     start_y = self._find_start_y(width)
    #     machining_limits = MachiningLimits()
    #     pocket = Pocket(
    #         start_x=start_x,
    #         start_y=start_y,
    #         start_depth=self.mill_depth,
    #         angle=0,
    #         inclination=0,
    #         slope=0.0,
    #         length=length,
    #         width=width,
    #         internal_angle=90.0,
    #         tilt_ref_side=90.0,
    #         tilt_end_side=math.degrees(tilt_end_side),
    #         tilt_opp_side=90.0,
    #         tilt_start_side=math.degrees(tilt_start_side),
    #         machining_limits=machining_limits.limits,
    #         ref_side_index=self.cross_beam_ref_side_index,
    #     )
    #     self.cross_beam.add_features(pocket)
    #     self.features.append(pocket)

    # def _compute_angle_and_dot_product(self, intersection_point):
    #     end, _ = self.main_beam.endpoint_closest_to_point(Point(*intersection_point))
    #     if end == "start":
    #         main_beam_direction = self.main_beam.centerline.vector
    #     else:
    #         main_beam_direction = self.main_beam.centerline.vector * -1
    #     angle = angle_vectors(main_beam_direction, self.cross_beam.centerline.direction)
    #     dot = dot_vectors(main_beam_direction, self.cross_beam.centerline.direction)
    #     return angle, dot

    # def _find_start_x(self, intersection_point, angle):
    #     beam_width, beam_height = self.main_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)
    #     _, cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)
    #     ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
    #     ref_side_plane = Plane.from_frame(ref_side)
    #     intersection_point_projected = ref_side_plane.projected_point(Point(*intersection_point))
    #     air_distance = ref_side.point.distance_to_point(intersection_point_projected)
    #     # Calculate start_x
    #     start_x = math.sqrt(air_distance**2 - (beam_width / 2) ** 2)
    #     x1 = (cross_height / 2 - self.mill_depth) / math.tan(math.pi - angle)
    #     x2 = (beam_height / 2) / math.sin(math.pi - angle)
    #     start_x -= x1
    #     start_x -= x2
    #     return start_x

    # def _find_length(self, angle):
    #     _, beam_height = self.main_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)
    #     length = beam_height / math.sin(angle)
    #     return length

    # def _find_start_y(self, width):
    #     cross_width, _ = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)
    #     start_y = (cross_width - width) / 2
    #     return start_y

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
