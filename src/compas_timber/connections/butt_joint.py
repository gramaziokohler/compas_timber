from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Plane
from compas.geometry import Polyhedron
from compas.geometry import Vector

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.geometry import polyhedron_from_box_planes

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence

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
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.
    features: list[BTLxProcessing]
        List of features to be applied to the cross beam and main beam.
    cross_beam_ref_side_index : int
        The index of the side of the cross beam relative to the main beam..
    main_beam_ref_side_index : int
        The index of the side of the main beam relative to the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(ButtJoint, self).__data__
        data["mill_depth"] = self.mill_depth
        data["butt_plane"] = self.butt_plane
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(
        self,
        main_beam: Beam = None,
        cross_beam: Beam = None,
        mill_depth: Optional[float] = None,
        butt_plane: Optional[Plane] = None,
        force_pocket: bool = False,
        conical_tool: bool = False,
        **kwargs,
    ):
        super(ButtJoint, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.mill_depth = mill_depth
        self.force_pocket = force_pocket
        self.conical_tool = conical_tool
        self.features = []
        self._butt_plane = butt_plane

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
        if self._butt_plane is None:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            cutting_plane.xaxis = -cutting_plane.xaxis
            if self.mill_depth:
                cutting_plane.translate(cutting_plane.normal * self.mill_depth)
            self._butt_plane = Plane.from_frame(cutting_plane)
        return self._butt_plane

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

    def get_kinematic_constraint(self, moving_element):
        """Calculates the escape constraint for the Butt joint.
        
        Returns a Plane representing the 2-DOF sliding freedom if there is a pocket/lap,
        otherwise returns a Vector representing a 3-DOF half-space.
        """
        if moving_element not in self.elements:
            raise ValueError("Element is not part of this joint.")

        if moving_element == self.cross_beam:
            normal = self.butt_plane.normal
            
        elif moving_element == self.main_beam:
            normal = self.butt_plane.copy().normal * -1
            
        if self.mill_depth:
            side_a_normal = Plane.from_frame(self.main_beam.ref_sides[self.main_beam_ref_side_index]).normal * -1
            side_b_normal = Plane.from_frame(self.main_beam.opp_side(self.main_beam_ref_side_index)).normal * -1
            
            return [normal, side_a_normal, side_b_normal]
        else:
            return [normal]
