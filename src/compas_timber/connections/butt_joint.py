from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import centroid_points
from compas.geometry import intersection_plane_plane_plane

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence

if TYPE_CHECKING:
    from compas_timber.elements.beam import Beam
    from compas_timber.model.model import TimberModel
    from src.compas_timber.fabrication.btlx import BTLxProcessing


class ButtJoint(Joint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
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
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.
    features: list[BTLxProcessing]
        List of features to be applied to the cross beam and main beam.

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

    def __init__(
        self,
        main_beam: Beam = None,
        cross_beam: Beam = None,
        mill_depth: Optional[float] = None,
        modify_cross: bool = True,
        butt_plane: Optional[Plane] = None,
        force_pocket: bool = False,
        conical_tool: bool = False,
        **kwargs,
    ):
        super(ButtJoint, self).__init__(**kwargs)
        self.main_beam: Beam = main_beam
        self.cross_beam: Beam = cross_beam
        self.main_beam_guid: str = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid: str = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.mill_depth: float = mill_depth or 0.0
        self.modify_cross: bool = modify_cross
        self.butt_plane: Optional[Plane] = butt_plane
        self.force_pocket: bool = force_pocket
        self.conical_tool: bool = conical_tool
        self.features: list[BTLxProcessing] = []

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

    def add_features(self) -> None:
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.
        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        self._apply_cut_to_main_beam()

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

    def _apply_cut_to_main_beam(self):
        feature = ButtJoint.cut_main_beam(self.cross_beam, self.main_beam, self.mill_depth, self.butt_plane)
        self.main_beam.add_features(feature)
        self.features.append(feature)

    def _apply_lap_to_cross_beam(self):
        feature = ButtJoint.lap_on_cross_beam(self.cross_beam, self.main_beam, self.mill_depth, self.butt_plane)
        if feature:
            self.cross_beam.add_features(feature)
            self.features.append(feature)

    def _apply_pocket_to_cross_beam(self):
        pocket = ButtJoint.pocket_on_cross_beam(self.cross_beam, self.main_beam, self.mill_depth, self.butt_plane, self.conical_tool)
        self.cross_beam.add_features(pocket)
        self.features.append(pocket)

    def restore_beams_from_keys(self, model: TimberModel):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]

    @staticmethod
    def cut_main_beam(cross_beam: Beam, main_beam: Beam, mill_depth: Optional[float] = None, butt_plane: Optional[Plane] = None) -> JackRafterCutProxy:
        if butt_plane:
            cutting_plane = butt_plane
        else:
            ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            cutting_plane = cross_beam.ref_sides[cross_beam_ref_side_index]
            cutting_plane.xaxis = -cutting_plane.xaxis

            if mill_depth:
                cutting_plane.translate(cutting_plane.normal * mill_depth)

        ref_side_dict = beam_ref_side_incidence(cross_beam, main_beam, ignore_ends=True)
        main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

        feature = JackRafterCutProxy.from_plane_and_beam(cutting_plane, main_beam, main_beam_ref_side_index)

        return feature

    @staticmethod
    def lap_on_cross_beam(cross_beam: Beam, main_beam: Beam, mill_depth: Optional[float] = None, butt_plane: Optional[Plane] = None) -> Lap:
        if mill_depth and not butt_plane:
            ref_side_dict = beam_ref_side_incidence(cross_beam, main_beam, ignore_ends=True)
            main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

            cutting_plane = main_beam.ref_sides[main_beam_ref_side_index]

            _, lap_width = main_beam.get_dimensions_relative_to_side(main_beam_ref_side_index)
            ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

            lap_feature = Lap.from_plane_and_beam(cutting_plane, cross_beam, lap_width, mill_depth, ref_side_index=cross_beam_ref_side_index)

            return lap_feature

    @staticmethod
    def pocket_on_cross_beam(cross_beam: Beam, main_beam: Beam, mill_depth: Optional[float] = None, butt_plane: Optional[Plane] = None, conical_tool: bool = False) -> Pocket:
        ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
        cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)

        cutting_plane = cross_beam.ref_sides[cross_beam_ref_side_index]
        cutting_plane.xaxis = -cutting_plane.xaxis
        if mill_depth:
            cutting_plane.translate(cutting_plane.normal * mill_depth)

        main_beam_ref_sides = list(main_beam.ref_sides)
        plane_0 = Plane.from_frame(main_beam_ref_sides[0])
        plane_1 = Plane.from_frame(main_beam_ref_sides[1])
        plane_2 = Plane.from_frame(main_beam_ref_sides[2])
        plane_3 = Plane.from_frame(main_beam_ref_sides[3])
        cutting_plane = Plane.from_frame(cutting_plane)
        top_plane = Plane.from_frame(cross_beam.ref_sides[cross_beam_ref_side_index])
        vertices = [
            Point(*intersection_plane_plane_plane(plane_2, plane_3, cutting_plane)),  # v0
            Point(*intersection_plane_plane_plane(plane_0, plane_3, cutting_plane)),  # v1
            Point(*intersection_plane_plane_plane(plane_1, plane_0, cutting_plane)),  # v2
            Point(*intersection_plane_plane_plane(plane_2, plane_1, cutting_plane)),  # v3
            Point(*intersection_plane_plane_plane(plane_2, plane_3, top_plane)),  # v4
            Point(*intersection_plane_plane_plane(plane_0, plane_3, top_plane)),  # v5
            Point(*intersection_plane_plane_plane(plane_1, plane_0, top_plane)),  # v6
            Point(*intersection_plane_plane_plane(plane_2, plane_1, top_plane)),  # v7
        ]
        faces = [[0, 3, 2, 1], [1, 2, 6, 5], [2, 3, 7, 6], [0, 4, 7, 3], [0, 1, 5, 4], [4, 5, 6, 7]]
        faces = ButtJoint._ensure_faces_outward(vertices, faces)
        cutout_volume = Polyhedron(vertices, faces)
        # return cutout_volume
        pocket = Pocket.from_volume_and_element(cutout_volume, cross_beam, ref_side_index=cross_beam_ref_side_index)
        if not conical_tool:
            pocket.tilt_start_side = 90 if pocket.tilt_start_side < 90 else pocket.tilt_start_side
            pocket.tilt_end_side = 90 if pocket.tilt_end_side < 90 else pocket.tilt_end_side
            pocket.tilt_ref_side = 90 if pocket.tilt_ref_side < 90 else pocket.tilt_ref_side
            pocket.tilt_opp_side = 90 if pocket.tilt_opp_side < 90 else pocket.tilt_opp_side
        return pocket

    @staticmethod
    def _ensure_faces_outward(vertices: list[Point], faces: list[list[int]]):
        """Reorder face indices so face normals point outward.
        Parameters
        ----------
        vertices : list[Point]
            list of Point or 3-tuples
        faces : list[list[int]]
            list of lists of indices

        Returns
        -------
        list[list[int]]
            new faces order
        """
        poly_centroid = Point(*centroid_points(vertices))
        new_faces = []
        for face in faces:
            # vertices
            v0 = vertices[face[0]]
            v1 = vertices[face[1]]
            v2 = vertices[face[2]]
            # vectors
            e1 = Vector.from_start_end(v0, v1)
            e2 = Vector.from_start_end(v0, v2)
            n = e1.cross(e2)
            face_centroid = centroid_points([vertices[i] for i in face])
            outward = Vector.from_start_end(poly_centroid, face_centroid)
            # dots
            if n.dot(outward) < 0:
                new_faces.append(list(reversed(face)))
            else:
                new_faces.append(list(face))
        return new_faces
