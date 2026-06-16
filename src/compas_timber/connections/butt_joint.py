from __future__ import annotations

import math
from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Plane
from compas.geometry import Polyhedron
from compas.geometry import dot_vectors
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.geometry import polyhedron_from_box_planes

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import decompose_plane_to_ref_side
from .utilities import plane_from_ref_side_angle_offset

if TYPE_CHECKING:
    from compas_timber.elements.beam import Beam


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
    beams : list[:class:`~compas_timber.elements.Beam`]
        A list containing the main beam and the cross beam.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.
    features: list[:class:`~compas_timber.fabrication.BTLxProcessing`]
        List of features to be applied to the cross beam and main beam.
    cross_beam_ref_side_index : int
        The index of the side of the cross beam relative to the main beam.
    main_beam_ref_side_index : int
        The index of the side of the main beam relative to the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(ButtJoint, self).__data__
        data["mill_depth"] = self.mill_depth
        data["butt_plane_ref_side_index"] = self.butt_plane_ref_side_index
        data["butt_plane_angle"] = self.butt_plane_angle
        data["butt_plane_offset"] = self.butt_plane_offset
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(
        self,
        main_beam: Beam = None,
        cross_beam: Beam = None,
        mill_depth: Optional[float] = None,
        butt_plane_ref_side_index: Optional[int] = None,
        butt_plane_angle: Optional[float] = None,
        butt_plane_offset: Optional[float] = None,
        force_pocket: bool = False,
        conical_tool: bool = False,
        **kwargs,
    ):
        super(ButtJoint, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.mill_depth: float = mill_depth or 0.0
        self.butt_plane_ref_side_index: Optional[int] = butt_plane_ref_side_index
        self.butt_plane_angle: float = butt_plane_angle if butt_plane_angle is not None else 0.0
        self.butt_plane_offset: float = butt_plane_offset if butt_plane_offset is not None else 0.0
        self.force_pocket: bool = force_pocket
        self.conical_tool: bool = conical_tool
        self.features = []

    @property
    def main_beam(self):
        return self.element_a

    @property
    def cross_beam(self):
        return self.element_b

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
    def butt_plane(self) -> Plane:
        """The plane used to cut the main beam.

        Computed from `butt_plane_ref_side_index`/`butt_plane_angle`/`butt_plane_offset`. Always valid: if no override
        is set, defaults to the cross beam's side closest to the main beam, offset outward by `mill_depth`.
        """
        if self.butt_plane_ref_side_index is not None:
            ref_side = self.cross_beam.ref_sides[self.butt_plane_ref_side_index]
            return plane_from_ref_side_angle_offset(ref_side, self.butt_plane_angle, self.butt_plane_offset)
        # default: the cross beam's closest side, facing the main beam, offset by mill_depth
        ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        return plane_from_ref_side_angle_offset(ref_side, math.pi, self.mill_depth)

    def _back_cutting_plane(self) -> Plane:
        """The plane used to extend/cut the cross beam when `modify_cross` is True.

        Defaults to the side of the main beam opposite the one facing the cross beam. `LButtJoint` overrides this to
        support a user-defined `back_plane`; this is not a general `ButtJoint` concept.
        """
        return Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index))

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.
        """
        assert self.main_beam and self.cross_beam
        # extend the main beam
        try:
            start, end = self.main_beam.extension_to_plane(self.butt_plane)
            extension_tolerance = 0
            # extension_tolerance = 0.01 if TOL.unit == "M" else 10
            joint_id = self.guid
            self.main_beam.add_blank_extension(start + extension_tolerance, end + extension_tolerance, joint_id)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[self.butt_plane])
        except Exception as ex:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))

    def add_features(self) -> None:
        """Removes this joint's previously generated features and adds new features to each beam."""
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
                cross_feature = Pocket.from_volume_and_element(
                    milling_volume,
                    self.cross_beam,
                    allow_undercut=self.conical_tool,
                    ref_side_index=self.cross_beam_ref_side_index,
                )
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

    def _get_milling_volume_for_pocket(self) -> Polyhedron:
        top_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index])
        bottom_plane = self.butt_plane
        side_a_plane = Plane.from_frame(self.main_beam.ref_sides[self.main_beam_ref_side_index])
        side_b_plane = Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index))
        end_a_plane = Plane.from_frame(self.main_beam.front_side(self.main_beam_ref_side_index))
        end_b_plane = Plane.from_frame(self.main_beam.back_side(self.main_beam_ref_side_index))

        return polyhedron_from_box_planes(bottom_plane, top_plane, side_a_plane, side_b_plane, end_a_plane, end_b_plane)

    @staticmethod
    def butt_plane_args(main_beam: "Beam", cross_beam: "Beam", butt_plane: Plane) -> dict:
        """Returns kwargs encoding `butt_plane` (world coordinates) as `butt_plane_ref_side_index`/`butt_plane_angle`/`butt_plane_offset`.

        Pass the returned dict as keyword arguments to :meth:`~compas_timber.connections.Joint.create`.

        Parameters
        ----------
        main_beam : :class:`~compas_timber.elements.Beam`
        cross_beam : :class:`~compas_timber.elements.Beam`
        butt_plane : :class:`~compas.geometry.Plane`
            A plane in world coordinates used to cut the main beam. Must be parallel to the cross beam's centerline
            (normal perpendicular to the cross beam's length direction).

        Returns
        -------
        dict
            Keys: ``butt_plane_ref_side_index``, ``butt_plane_angle``, ``butt_plane_offset``.

        """
        if not TOL.is_zero(dot_vectors(cross_beam.frame.xaxis, butt_plane.normal)):
            raise ValueError("butt_plane normal must be perpendicular to cross_beam centerline axis")

        ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        ref_side = cross_beam.ref_sides[ref_side_index]
        angle, offset = decompose_plane_to_ref_side(ref_side, butt_plane, plane_name="butt_plane", reference_name="cross_beam")
        return {
            "butt_plane_ref_side_index": ref_side_index,
            "butt_plane_angle": angle,
            "butt_plane_offset": offset,
        }
