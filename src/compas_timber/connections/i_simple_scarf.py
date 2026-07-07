from __future__ import annotations

import math
from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Tuple

from compas.geometry import Plane
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence_with_vector

if TYPE_CHECKING:
    from compas.geometry import Frame
    from compas.geometry import Point

    from compas_timber.elements import Beam


class ISimpleScarf(Joint):
    """Represents a Simple Scarf joint for two parallel beams (Topology I).

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`, optional
        The first beam of the joint.
    cross_beam : :class:`~compas_timber.elements.Beam`, optional
        The second beam of the joint, parallel to the main beam.
    length : float, optional
        The length of the scarf overlap along the beam axis. If not provided,
        defaults to ``DEFAULT_LENGTH_TO_HEIGHT_RATIO`` times the beam height.
    depth_ref_side : float, optional
        The cut depth on the reference side of the beam. If not provided,
        defaults to ``DEFAULT_DEPTH_TO_HEIGHT_RATIO`` times the beam height.
    depth_opp_side : float, optional
        The cut depth on the opposite side of the beam. If not provided,
        defaults to ``DEFAULT_DEPTH_TO_HEIGHT_RATIO`` times the beam height.
    num_drill_hole : int, optional
        Number of drill holes through the joint (0, 1, or 2). Defaults to 0.
    drill_hole_diam : float, optional
        Diameter of the drill holes in mm. Defaults to 20.0.
    ref_side_index : int, optional
        Zero-based index of the reference side (RS1–RS6 → 0–5). Defaults to 0.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The first beam of the joint (alias for ``element_a``).
    cross_beam : :class:`~compas_timber.elements.Beam`
        The second beam of the joint (alias for ``element_b``).
    main_beam_ref_side_index : int
        Reference side index for the main beam. Equal to ``ref_side_index``.
    cross_beam_ref_side_index : int
        Reference side index for the cross beam, resolved automatically from
        the face most aligned with the main beam's reference side normal.
    origin : :class:`~compas.geometry.Point`
        The origin point of the joint (alias for ``location``).
    length : float
        The length of the scarf overlap.
    depth_ref_side : float
        The cut depth on the reference side.
    depth_opp_side : float
        The cut depth on the opposite side.
    num_drill_hole : int
        Number of drill holes (0, 1, or 2).
    drill_hole_diam : float
        Diameter of the drill holes in mm.
    ref_side_index : int
        Zero-based index of the reference side used for the main beam.
    features : list
        List of :class:`~compas_timber.fabrication.SimpleScarf` features
        added to the beams by this joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_I

    # Scarf length defaults to 3x the beam height — a common rule of thumb
    # that provides enough glue/contact area for structural performance.
    DEFAULT_LENGTH_TO_HEIGHT_RATIO = 3
    # Depth on each face defaults to 1/4 of the beam height,
    # leaving the middle half as the straight (uncut) section.
    DEFAULT_DEPTH_TO_HEIGHT_RATIO = 0.25

    @property
    def __data__(self):
        data = super(ISimpleScarf, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["length"] = self.length
        data["depth_ref_side"] = self.depth_ref_side
        data["depth_opp_side"] = self.depth_opp_side
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam"] = self.drill_hole_diam
        data["ref_side_index"] = self.ref_side_index
        return data

    def __init__(
        self,
        main_beam: Optional[Beam] = None,
        cross_beam: Optional[Beam] = None,
        length: Optional[float] = None,
        depth_ref_side: Optional[float] = None,
        depth_opp_side: Optional[float] = None,
        num_drill_hole: int = 0,
        drill_hole_diam: float = 20.0,
        ref_side_index: int = 0,
        **kwargs,
    ):
        super(ISimpleScarf, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.main_beam_guid = kwargs.get("main_beam_guid") or (str(main_beam.guid) if main_beam else None)
        self.cross_beam_guid = kwargs.get("cross_beam_guid") or (str(cross_beam.guid) if cross_beam else None)

        self.length = length
        self.depth_ref_side = depth_ref_side
        self.depth_opp_side = depth_opp_side
        self.num_drill_hole = num_drill_hole
        self.drill_hole_diam = drill_hole_diam
        self.ref_side_index = ref_side_index

        self.features = []

        if self.main_beam and self.cross_beam:
            self._set_unset_attributes()

    @property
    def main_beam(self) -> Beam:
        return self.element_a

    @property
    def cross_beam(self) -> Beam:
        return self.element_b

    @property
    def main_beam_ref_side_index(self) -> int:
        return self.ref_side_index

    @property
    def cross_beam_ref_side_index(self) -> int:
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, self.main_beam.ref_sides[self.main_beam_ref_side_index].normal, ignore_ends=True)
        return max(ref_side_dict, key=ref_side_dict.get)

    @property
    def origin(self) -> Point:
        return self.location

    def _get_beam_side(self, beam: Beam) -> str:
        """Finds whether the scarf end of the beam is its start or end.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to evaluate.

        Returns
        -------
        str
            ``"start"`` or ``"end"`` depending on which endpoint of the beam
            is closest to the joint origin.
        """
        side, _ = beam.endpoint_closest_to_point(self.origin)
        return side

    def extension_plane(self, beam: Beam) -> Tuple[int, Frame]:
        """Returns the end-face index and frame used to compute the blank extension for a beam.

        The end face is RS5 (index 4) when the scarf sits at the beam start,
        or RS6 (index 5) when it sits at the beam end.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam for which to determine the extension plane.

        Returns
        -------
        tuple(int, :class:`~compas.geometry.Frame`)
            A tuple of ``(ext_side_index, frame)`` where ``ext_side_index`` is
            the zero-based index of the end face (4 or 5) and ``frame`` is the
            corresponding reference-side frame.
        """
        ext_side_index = 4 if self._get_beam_side(beam) == "start" else 5
        return ext_side_index, beam.ref_sides[ext_side_index]

    def add_extensions(self) -> None:
        """Calculates and adds the required blank extensions to both beams."""
        assert self.main_beam and self.cross_beam

        try:
            _, main_extension_frame = self.extension_plane(self.main_beam)
            main_extension_frame.translate(main_extension_frame.normal * self.length / 2)

            _, cross_extension_frame = self.extension_plane(self.cross_beam)
            cross_extension_frame.translate(cross_extension_frame.normal * self.length / 2)

            start_a, end_a = self.main_beam.extension_to_plane(Plane.from_frame(main_extension_frame))
            start_b, end_b = self.cross_beam.extension_to_plane(Plane.from_frame(cross_extension_frame))

        except AttributeError as ae:
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=[main_extension_frame])
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))

        self.main_beam.add_blank_extension(start_a, end_a, self.guid)
        self.cross_beam.add_blank_extension(start_b, end_b, self.guid)

    def add_features(self) -> None:
        """Generates and assigns the SimpleScarf fabrication features.

        Raises
        ------
        AssertionError
            If either beam is not set.
        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)
            self.features = []

        main_feature = SimpleScarf.from_beam_and_side(
            self.main_beam,
            side=self._get_beam_side(self.main_beam),
            length=self.length,
            depth_ref_side=self.depth_ref_side,
            depth_opp_side=self.depth_opp_side,
            num_drill_hole=self.num_drill_hole,
            drill_hole_diam=self.drill_hole_diam,
            ref_side_index=self.ref_side_index,
        )

        cross_feature = SimpleScarf.from_beam_and_side(
            self.cross_beam,
            side=self._get_beam_side(self.cross_beam),
            length=self.length,
            depth_ref_side=self.depth_opp_side,
            depth_opp_side=self.depth_ref_side,
            num_drill_hole=self.num_drill_hole,
            drill_hole_diam=self.drill_hole_diam,
            ref_side_index=self.cross_beam_ref_side_index,
        )

        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        self.features.extend([main_feature, cross_feature])

    @classmethod
    def check_elements_compatibility(cls, elements: List[Beam], raise_error: bool = False) -> bool:
        """Checks if the two beams are parallel, as required for an ISimpleScarf joint.

        Parameters
        ----------
        elements : list(:class:`~compas_timber.elements.Beam`)
            The two beams to check.
        raise_error : bool, optional
            If ``True``, raise a :class:`~compas_timber.errors.BeamJoiningError`
            instead of returning ``False``. Defaults to ``False``.

        Returns
        -------
        bool
            ``True`` if the beams are parallel, ``False`` otherwise
            (when ``raise_error`` is ``False``).

        Raises
        ------
        :class:`~compas_timber.errors.BeamJoiningError`
            If the beams are not parallel and ``raise_error`` is ``True``.
        """
        dot = abs(elements[0].centerline.direction.dot(elements[1].centerline.direction))
        if not TOL.is_close(dot, 1):
            if not raise_error:
                return False
            raise BeamJoiningError(elements, cls, debug_info="The two beams are not parallel to create a Simple Scarf joint.")
        return True

    def _set_unset_attributes(self) -> None:
        """Sets attributes that were not provided at initialization based on the geometry of the beams."""
        width, height = self.main_beam.get_dimensions_relative_to_side(self.ref_side_index)

        if self.length is None:
            self.length = height * self.DEFAULT_LENGTH_TO_HEIGHT_RATIO

        if self.depth_ref_side is None:
            self.depth_ref_side = height * self.DEFAULT_DEPTH_TO_HEIGHT_RATIO

        if self.depth_opp_side is None:
            self.depth_opp_side = height * self.DEFAULT_DEPTH_TO_HEIGHT_RATIO

    def get_kinematic_constraint(self, moving_element):
        """Calculates the escape constraint for the ISimpleScarf joint."""
        if moving_element not in self.elements:
            raise ValueError("Element is not part of this joint.")
        
        width, height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)
        scarf_depth = height - (self.depth_ref_side + self.depth_opp_side)
        scarf_angle = math.atan((scarf_depth/self.length))
            
        if moving_element == self.main_beam:
            beam_side = self._get_beam_side(self.main_beam)
            if beam_side == "start":
                end_vector = self.main_beam.centerline.direction
                opp_frame = self.main_beam.opp_side(self.main_beam_ref_side_index)
                scarf_normal = opp_frame.rotated((scarf_angle * -1), opp_frame.yaxis, opp_frame.point).normal
            else:
                end_vector = self.main_beam.centerline.direction * -1
                opp_frame = self.main_beam.opp_side(self.main_beam_ref_side_index)
                scarf_normal = opp_frame.rotated(scarf_angle, opp_frame.yaxis, opp_frame.point).normal
            
        elif moving_element == self.cross_beam:
            beam_side = self._get_beam_side(self.cross_beam)
            if beam_side == "start":
                end_vector = self.cross_beam.centerline.direction
                opp_frame = self.cross_beam.opp_side(self.cross_beam_ref_side_index)
                scarf_normal = opp_frame.rotated((scarf_angle * -1), opp_frame.yaxis, opp_frame.point).normal
            else:
                end_vector = self.cross_beam.centerline.direction * -1
                opp_frame = self.cross_beam.opp_side(self.cross_beam_ref_side_index)
                scarf_normal = opp_frame.rotated(scarf_angle, opp_frame.yaxis, opp_frame.point).normal

        return [scarf_normal, end_vector]
