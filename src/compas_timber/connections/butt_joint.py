from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Plane
from compas.geometry import Polyhedron

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.utils import polyhedron_from_box_planes

from .joint import Joint
from .utilities import beam_ref_side_incidence

if TYPE_CHECKING:
    from compas_timber.elements import Beam
    from compas_timber.fabrication import BTLxProcessing
    from compas_timber.model import TimberModel


class ButtJoint(Joint):
    """Base class for Butt joints, where the main beam is trimmed and butts against the cross beam.

    Not intended to be used directly. Use :class:`~compas_timber.connections.LButtJoint` or
    :class:`~compas_timber.connections.TButtJoint` to create an instance and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined. This beam is trimmed at the joint.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined. This beam receives the pocket or lap feature.
    mill_depth : float, optional
        The depth by which the butt plane is offset into the cross beam, creating a pocket or lap.
        Ignored if `butt_plane` is provided explicitly.
    modify_cross : bool, default False
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    back_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the cross beam. If not provided, the back side of the main beam will be used.
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
        The depth by which the butt plane is offset into the cross beam.
    modify_cross : bool
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    butt_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the main beam. Returns the explicitly set plane if provided,
        otherwise derived from the nearest face of the cross beam offset by `mill_depth`.
    back_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the cross beam. Returns the explicitly set plane if provided,
        otherwise derived from the opposite face of the main beam.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.
    features: list[BTLxProcessing]
        List of features to be applied to the cross beam and main beam.

    """

    @property
    def __data__(self):
        data = super(ButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["mill_depth"] = self.mill_depth
        data["modify_cross"] = self.modify_cross
        data["butt_plane"] = self._butt_plane
        data["back_plane"] = self._back_plane
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(
        self,
        main_beam: Beam = None,
        cross_beam: Beam = None,
        mill_depth: Optional[float] = None,
        modify_cross: bool = False,
        butt_plane: Optional[Plane] = None,
        back_plane: Optional[Plane] = None,
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
        self.force_pocket: bool = force_pocket
        self.conical_tool: bool = conical_tool
        self.features: list[BTLxProcessing] = []

        self._butt_plane: Optional[Plane] = butt_plane
        self._back_plane: Optional[Plane] = back_plane

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

    @property
    def butt_plane(self):
        if self._butt_plane:
            return self._butt_plane
        cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        cutting_plane.xaxis = -cutting_plane.xaxis
        if self.mill_depth:
            cutting_plane.translate(cutting_plane.normal * self.mill_depth)
        return Plane.from_frame(cutting_plane)

    @butt_plane.setter
    def butt_plane(self, plane):
        self._butt_plane = plane

    @property
    def back_plane(self):
        if self._back_plane:
            return self._back_plane
        return Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index))

    @back_plane.setter
    def back_plane(self, plane):
        self._back_plane = plane

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
            start_main, end_main = self.main_beam.extension_to_plane(self.butt_plane)
            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.main_beam.add_blank_extension(
                start_main + extension_tolerance,
                end_main + extension_tolerance,
                self.guid,
            )
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[self.butt_plane])
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        # extend the cross beam
        if self.modify_cross:
            try:
                start_cross, end_cross = self.cross_beam.extension_to_plane(self.back_plane)
            except AttributeError as ae:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[self.back_plane])
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

        # apply cut on the main beam
        main_feature = JackRafterCutProxy.from_plane_and_beam(self.butt_plane, self.main_beam, self.main_beam_ref_side_index)
        self.main_beam.add_features(main_feature)
        self.features.append(main_feature)

        # apply lap or pocket on the cross beam
        if self.mill_depth:
            if self.force_pocket:
                milling_volume = self._get_milling_volume_for_pocket()
                cross_feature = Pocket.from_volume_and_element(milling_volume, self.cross_beam, ref_side_index=self.cross_beam_ref_side_index)
                if not self.conical_tool:
                    self._limit_pocket_tilt_angles(cross_feature)
            else:
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

        # apply a refinement cut on the cross beam
        if self.modify_cross:
            cross_refinement_feature = JackRafterCutProxy.from_plane_and_beam(self.back_plane, self.cross_beam, self.cross_beam_ref_side_index)
            self.cross_beam.add_features(cross_refinement_feature)
            self.features.append(cross_refinement_feature)

    def restore_beams_from_keys(self, model: TimberModel):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]

    def _get_milling_volume_for_pocket(self) -> Polyhedron:
        top_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index])
        bottom_plane = self.butt_plane
        side_a_plane = Plane.from_frame(self.main_beam.ref_sides[self.main_beam_ref_side_index])
        side_b_plane = Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index))
        end_a_plane = Plane.from_frame(self.main_beam.front_side(self.main_beam_ref_side_index))
        end_b_plane = Plane.from_frame(self.main_beam.back_side(self.main_beam_ref_side_index))

        return polyhedron_from_box_planes(bottom_plane, top_plane, side_a_plane, side_b_plane, end_a_plane, end_b_plane)

    @staticmethod
    def _limit_pocket_tilt_angles(pocket: Pocket) -> None:
        # limits the tilt angles of the pocket to 90 degrees to be compatible with non-conical tools
        pocket.tilt_start_side = 90 if pocket.tilt_start_side < 90 else pocket.tilt_start_side
        pocket.tilt_end_side = 90 if pocket.tilt_end_side < 90 else pocket.tilt_end_side
        pocket.tilt_ref_side = 90 if pocket.tilt_ref_side < 90 else pocket.tilt_ref_side
        pocket.tilt_opp_side = 90 if pocket.tilt_opp_side < 90 else pocket.tilt_opp_side
