from __future__ import annotations

from typing import Optional

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_brep import Brep

from compas_timber.fabrication import Pocket
from compas_timber.fabrication import Slot

from .anchor import AnchorKind
from .dowel import Dowel
from .fastener import Fastener
from .fastener import FastenerPart


class StekoJointType:
    """The anatomy of a :class:`~compas_timber.connections.StekoJoint`: how many beams meet the column and how.

    Published by the joint (see :attr:`~compas_timber.connections.StekoJoint.joint_type`) and consumed by
    :meth:`StekoFastener.bind` to decide how to lay out plates and dowels.
    """

    SOLO_BEAM = 0
    DOUBLE_LINEAR_BEAM = 1
    DOUBLE_ANGLED_BEAM = 2
    TRIPLE_BEAM = 3
    QUADRUPLE_BEAM = 4


class StekoPlate(FastenerPart):
    """Describes the flat steel plate of a Steko connector, embedded in a slot machined into the beam.

    The plate geometry is defined in the part's local coordinate system (centered on the world XY frame); its
    placement in the model is expressed by the element ``transformation`` (see
    :class:`~compas_timber.fasteners.FastenerPart`).

    Parameters
    ----------
    length : float
        The extent of the plate across the beam's end face (the ``length`` a :class:`~compas_timber.fabrication.Slot`
        computes for that face).
    depth : float
        How far the plate is embedded into the beam, measured along the beam's length.
    thickness : float
        The thickness of the plate, i.e. the width of the slot it sits in.
    frame : Frame, optional
        The placement frame of the plate. Defaults to the world XY frame.

    Attributes
    ----------
    length : float
        The extent of the plate across the beam's end face.
    depth : float
        How far the plate is embedded into the beam.
    thickness : float
        The thickness of the plate.
    geometry : Brep
        The geometry of the plate as a Brep, in model coordinates.
    """

    @property
    def __data__(self):
        return {
            "length": self.length,
            "depth": self.depth,
            "slot_depth": self.slot_depth,
            "thickness": self.thickness,
            "placement_frame": self.placement_frame,
            "element_guids": self.element_guids,
        }

    def __init__(self, length: float, depth: float, slot_depth: float, thickness: float, placement_frame: Optional[Frame] = None, **kwargs):
        super().__init__(frame=placement_frame, **kwargs)
        self.length = length
        self.depth = depth
        self.slot_depth = slot_depth
        self.thickness = thickness

    @property
    def _local_frame(self) -> Frame:
        # the plate geometry is defined relative to this frame; its zaxis is the slot's thickness (kerf) direction
        return Frame.worldXY()

    @property
    def blank_geometry(self) -> Box:
        return Box(self.depth, self.length, self.thickness, frame=self._local_frame)

    def compute_elementgeometry(self, include_features: bool = False) -> Brep:
        return Brep.from_box(self.blank_geometry)

    def apply_fastening_features(self) -> None:
        """Cut a :class:`~compas_timber.fabrication.Slot` into each beam in :attr:`elements` and a shared
        :class:`~compas_timber.fabrication.Pocket` into the column.

        A plate normally spans a single beam and the column (``elements == [column, beam]``), but a plate shared by
        a linear pair of beams (``elements == [column, beam_a, beam_b]``) cuts a slot into every beam it references,
        sized identically for each, while the pocket it cuts into the column is cut only once.
        """
        frame = self.frame  # placement frame in model coordinates
        plane = Plane(frame.point, frame.zaxis)
        column = self.elements[0]

        for beam in self.elements[1:]:
            slot = Slot.from_plane_and_beam(plane, beam, depth=self.slot_depth + column.width / 2, thickness=self.thickness)
            beam.add_feature(slot)
            self.applied_features.append(slot)

        box = self.blank_geometry.transformed(Transformation.from_frame(Frame.from_plane(plane)))
        pocket = Pocket.from_volume_and_element(box.to_mesh(), column)
        column.add_feature(pocket)
        self.applied_features.append(pocket)


class StekoSwordPlate(StekoPlate):
    """A notched "Schwert" (sword/blade) plate, used where two beams meet the column at an angle.

    Where a linear pair's two beams sit on opposite sides of the column (see :class:`StekoPlate`), an angled pair
    meets the column at 90° to each other. Both beams' plates use the same ``length`` (``beam.height``), which for
    two horizontal beams meeting a vertical column both means "vertical extent" — so a beam_a plate and a beam_b
    plate span the *same* real-world height band at the corner. A plain rectangular plate would collide there; even
    a comb with the same tooth pattern on both would, since the pattern doesn't change under the 90° rotation that
    relates beam_a's plates to beam_b's. Real Steko hardware resolves this by making each beam's plates occupy a
    *different* set of height bands, so a solid tooth on one beam's plate always lines up with an empty gap on the
    other's, and a solid "shank" (which still embeds into the beam exactly like a plain :class:`StekoPlate`) gives
    way to a comb of teeth on the "blade" end that reaches into the corner.

    Both the plate's own rendered shape (:meth:`compute_elementgeometry`) and the pocket it cuts into the column
    (:meth:`apply_fastening_features`) are built from the same list of boxes (:attr:`_tooth_boxes`): one box per
    shank, one per tooth. Cutting a separate pocket per tooth (rather than one box spanning the whole comb) is what
    keeps the gaps between teeth actually empty in the column, instead of over-cutting them away.

    Parameters
    ----------
    shank_length : float, optional
        The length of each solid, rectangular shank, before the comb begins. Defaults to a third of ``depth``.
    double_shank : bool, optional
        If ``False`` (the default), the plate has a single shank — for a solo beam, embedding into that one beam,
        with the comb reaching from there to the corner (see :meth:`StekoFastener._bind_solo_beam` /
        :meth:`_bind_double_angled_beams`). If ``True``, the plate has a shank at *both* ends — for a pair of beams
        it spans (see :meth:`StekoFastener._merge_linear_pair`), one embedding into each beam — with the comb only
        in the middle, where it crosses the other beam's plates.
    finger_count : int, optional
        The number of teeth on this plate. The comb is divided into ``2 * finger_count`` equal height bands,
        alternating tooth/gap; ``finger_count`` of them are teeth. Defaults to 2.
    phase : int, optional
        Which set of alternating bands are teeth: ``0`` for the even bands, ``1`` for the odd ones — the exact
        complement, with zero overlap. :meth:`StekoFastener._bind_double_angled_beams` gives each of the two beams
        a different phase so their plates weave instead of colliding. Defaults to 0.
    """

    @property
    def __data__(self):
        data = super().__data__
        data["shank_length"] = self.shank_length
        data["double_shank"] = self.double_shank
        data["finger_count"] = self.finger_count
        data["phase"] = self.phase
        return data

    def __init__(
        self,
        length: float,
        depth: float,
        slot_depth: float,
        thickness: float,
        shank_length: Optional[float] = None,
        double_shank: bool = False,
        finger_count: int = 2,
        phase: int = 0,
        placement_frame: Optional[Frame] = None,
        **kwargs,
    ):
        super().__init__(length=length, depth=depth, slot_depth=slot_depth, thickness=thickness, placement_frame=placement_frame, **kwargs)
        self.shank_length = shank_length if shank_length is not None else depth / 3
        self.double_shank = double_shank
        self.finger_count = finger_count
        self.phase = phase

    @property
    def _shank_count(self) -> int:
        return 2 if self.double_shank else 1

    @property
    def _tooth_boxes(self) -> list:
        """The shank box(es) followed by one box per comb tooth, in local coordinates (local +x is the/a shank end,
        local -x is the comb/corner end — or the other shank end, if :attr:`double_shank` — matching
        :attr:`blank_geometry`'s ``Box(depth, length, thickness)`` convention).

        The comb is divided into ``2 * finger_count`` equal-width height bands; :attr:`phase` picks every other one
        as a tooth (the rest stay empty gaps), spanning the full comb depth like the tines of a real comb.
        """
        band_count = 2 * self.finger_count
        band_width = self.length / band_count
        comb_length = self.depth - self._shank_count * self.shank_length

        boxes = []
        shank_a = Box(self.shank_length, self.length, self.thickness, frame=self._local_frame)
        shank_a.translate(Vector(self.depth / 2 - self.shank_length / 2, 0, 0))
        boxes.append(shank_a)

        if self.double_shank:
            shank_b = Box(self.shank_length, self.length, self.thickness, frame=self._local_frame)
            shank_b.translate(Vector(-self.depth / 2 + self.shank_length / 2, 0, 0))
            boxes.append(shank_b)
            comb_center_x = 0.0
        else:
            comb_center_x = self.depth / 2 - self.shank_length - comb_length / 2

        for i in range(self.finger_count):
            band_index = 2 * i + self.phase
            y_center = self.length / 2 - (band_index + 0.5) * band_width
            tooth = Box(comb_length, band_width, self.thickness, frame=self._local_frame)
            tooth.translate(Vector(comb_center_x, y_center, 0))
            boxes.append(tooth)
        return boxes

    def compute_elementgeometry(self, include_features: bool = False) -> Brep:
        breps = [Brep.from_box(box) for box in self._tooth_boxes]
        return Brep.from_boolean_union_multi(*breps)

    def apply_fastening_features(self) -> None:
        """Cut a :class:`~compas_timber.fabrication.Slot` into each beam in :attr:`elements`, and one
        :class:`~compas_timber.fabrication.Pocket` per comb tooth (plus each shank) into the column, so the gaps
        between teeth are left uncut.
        """
        frame = self.frame  # placement frame in model coordinates
        plane = Plane(frame.point, frame.zaxis)
        column = self.elements[0]

        for beam in self.elements[1:]:
            slot = Slot.from_plane_and_beam(plane, beam, depth=self.slot_depth + column.width / 2, thickness=self.thickness)
            beam.add_feature(slot)
            self.applied_features.append(slot)

        boxes = self._tooth_boxes
        transformed_boxes = [box.transformed(Transformation.from_frame(Frame.from_plane(plane))) for box in boxes]

        # the shank(s) (boxes[:_shank_count]) are wide enough that Pocket's own ref_side auto-detection picks the
        # wrong column face for them; a (narrower) tooth detects the correct one reliably, so derive it from the
        # first tooth once and reuse it for every box, so the shanks and all teeth land on the same, correct face.
        ref_side_index = Pocket._get_optimal_ref_side_index(column, transformed_boxes[self._shank_count].to_mesh())
        for transformed_box in transformed_boxes:
            pocket = Pocket.from_volume_and_element(transformed_box.to_mesh(), column, ref_side_index=ref_side_index)
            column.add_feature(pocket)
            self.applied_features.append(pocket)


class StekoFastener(Fastener):
    """A fastener consisting of a pair of steel plates, each slotted into a beam, pinned in place with dowels.

    This is the "what" half of the anchor-based fastener system: it is joint-agnostic. It declares the kinds of
    anchor it consumes (``FACE`` for the plates, ``AXIS`` for the dowels) and, when bound to a set of anchors, stages
    one part per anchor.

    Parameters
    ----------
    plate_depth : float, optional
        How far each plate is embedded into its beam. Default is 0.255.
    plate_thickness : float, optional
        The thickness of each plate, i.e. the width of the slot it sits in. Default is 0.027.
    dowel_diameter : float, optional
        The diameter of the dowels. Default is 0.025.
    dowel_length : float, optional
        The length of the dowels. Default is 0.4.

    Attributes
    ----------
    ACCEPTS : tuple(:class:`~compas_timber.fasteners.AnchorKind`)
        The kinds of anchor this fastener binds to.
    """

    ACCEPTS = (AnchorKind.FACE, AnchorKind.AXIS)

    @property
    def __data__(self):
        data = super().__data__
        data["plate_depth"] = self.plate_depth
        data["plate_thickness"] = self.plate_thickness
        data["dowel_diameter"] = self.dowel_diameter
        data["dowel_length"] = self.dowel_length
        return data

    def __init__(
        self,
        plate_depth: float = 0.300 + 0.24,
        plate_thickness: float = 0.027,
        dowel_diameter: float = 0.025,
        dowel_length: float = 0.24,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.plate_depth = plate_depth
        self.plate_thickness = plate_thickness
        self.dowel_diameter = dowel_diameter
        self.dowel_length = dowel_length

    def bind(self, anchors: list, joint_type: Optional[int] = None) -> "StekoFastener":
        """Bind the fastener to a set of anchors, staging one plate or dowel part at each.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors to attach to. Every anchor must be of a kind this fastener accepts.
        joint_type : int, optional
            The :class:`StekoJointType` of the joint publishing ``anchors``, used to decide how plates and dowels
            are laid out. Defaults to ``StekoJointType.SOLO_BEAM``, i.e. one independent plate/dowel set per beam.

        Returns
        -------
        :class:`~compas_timber.fasteners.StekoFastener`
            The fastener itself, for chaining.

        Raises
        ------
        ValueError
            If any of the anchors are not of a kind this fastener accepts.
        NotImplementedError
            If ``joint_type`` is not yet supported.
        """
        anchors = list(anchors)
        wrong = [a for a in anchors if a.kind not in self.ACCEPTS]
        if wrong:
            raise ValueError(f"StekoFastener can only be bound to anchors of kind {self.ACCEPTS}, but got {wrong}")

        joint_type = StekoJointType.SOLO_BEAM if joint_type is None else joint_type
        if joint_type is StekoJointType.SOLO_BEAM:
            self._bind_solo_beam(anchors)
        elif joint_type is StekoJointType.DOUBLE_LINEAR_BEAM:
            self._bind_double_linear_beams(anchors)
        elif joint_type is StekoJointType.DOUBLE_ANGLED_BEAM:
            self._bind_double_angled_beams(anchors)
        elif joint_type is StekoJointType.TRIPLE_BEAM:
            self._bind_triple_beams(anchors)
        elif joint_type is StekoJointType.QUADRUPLE_BEAM:
            self._bind_quadruple_beams(anchors)
        else:
            raise ValueError(f"Unknown StekoJointType: {joint_type}")
        return self

    def _bind_face_and_axis_anchors(self, anchors: list, plate_cls: type) -> None:
        """Stage one independent plate (of ``plate_cls``) or dowel part per anchor, i.e. per beam.

        This is the layout for :attr:`StekoJointType.SOLO_BEAM` (plain :class:`StekoPlate`) and
        :attr:`StekoJointType.DOUBLE_ANGLED_BEAM` (notched :class:`StekoSwordPlate`, so the plates from the two
        perpendicular beams can weave past each other at the corner instead of colliding).
        """
        for anchor in anchors:
            if anchor.kind == AnchorKind.FACE:
                column = anchor.elements[0]
                beam = anchor.elements[1]

                # anchor sits on the face of the column (offset toward beam only, not the column's far side), but
                # the plate spans the column's full width plus the beam embed. This single translation (derived
                # from the plate's own depth and the column's width) re-centers it onto the column's far edge.
                plate = plate_cls(length=beam.height, depth=self.plate_depth, slot_depth=0.3, thickness=self.plate_thickness)
                plate.transform(Transformation.from_frame(anchor.frame))
                plate.transform(Translation.from_vector(anchor.frame.xaxis * (plate.depth / 2 - column.width)))
                plate.elements = list(anchor.elements)
                self.add_part(plate)
            elif anchor.kind == AnchorKind.AXIS:
                dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
                dowel.transform(Transformation.from_frame(anchor.frame))
                dowel.elements = list(anchor.elements)
                self.add_part(dowel)

    def _bind_solo_beam(self, anchors: list) -> None:
        """Stage one plain :class:`StekoPlate` or dowel part per anchor, i.e. per beam."""
        self._bind_face_and_axis_anchors(anchors, StekoPlate)

    def _bind_double_linear_beams(self, anchors: list) -> None:
        """Stage one dowel per ``AXIS`` anchor, as in :meth:`_bind_solo_beam`, but merge the ``FACE`` anchors.

        A linear pair's two beams point in opposite directions away from the column, so one beam's ``slot_front``
        anchor lands on the very same plane as the other beam's ``slot_back`` anchor. Rather than staging a separate
        plate per anchor (which would double-cut that shared plane), each such pair is merged into a single plate
        that spans both beams, all the way through the column.
        """
        face_anchors = []
        for anchor in anchors:
            if anchor.kind == AnchorKind.FACE:
                face_anchors.append(anchor)
            elif anchor.kind == AnchorKind.AXIS:
                dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
                dowel.transform(Transformation.from_frame(anchor.frame))
                dowel.elements = list(anchor.elements)
                self.add_part(dowel)

        # pair each "front" anchor of one beam with the "back" anchor of the other beam: they share the same plane
        fronts = [a for a in face_anchors if a.role == "slot_front"]
        backs = [a for a in face_anchors if a.role == "slot_back"]

        for anchor_a, anchor_b in zip(fronts, reversed(backs)):
            column = anchor_a.elements[0]
            beam_a = anchor_a.elements[1]
            beam_b = anchor_b.elements[1]

            # anchor_a sits on the face of the column (offset toward beam_a only, not centered), and the plate must
            # reach evenly past it into beam_b too. This single translation (half the column's width, back along
            # anchor_a's own xaxis) re-centers it to embed 0.3m into each beam.
            plate = StekoPlate(
                length=beam_a.height,
                depth=0.300 + 0.300 + 0.24,
                slot_depth=0.300,
                thickness=self.plate_thickness,
            )

            plate.transform(Transformation.from_frame(anchor_a.frame))
            plate.transform(Translation.from_vector(anchor_a.frame.xaxis * -(column.width / 2)))
            plate.elements = [column, beam_a, beam_b]
            self.add_part(plate)

    def _bind_double_angled_beams(self, anchors: list) -> None:
        """Stage one notched :class:`StekoSwordPlate` or dowel part per anchor, i.e. per beam.

        An angled pair's two beams meet the column at 90° to each other rather than sitting on opposite sides of
        it, so the four plates (two per beam, front and back) all converge on the same corner. Unlike
        :meth:`_bind_solo_beam`, each beam is given a different :attr:`StekoSwordPlate.phase`, so the two beams'
        plates use complementary sets of comb teeth and weave past each other there instead of colliding.
        """
        beam_phases = {}
        for anchor in anchors:
            if anchor.kind == AnchorKind.FACE:
                column = anchor.elements[0]
                beam = anchor.elements[1]
                if beam not in beam_phases:
                    beam_phases[beam] = len(beam_phases) % 2

                plate = StekoSwordPlate(
                    length=beam.height,
                    depth=self.plate_depth,
                    slot_depth=0.3,
                    thickness=self.plate_thickness,
                    phase=beam_phases[beam],
                )
                plate.transform(Transformation.from_frame(anchor.frame))
                plate.transform(Translation.from_vector(anchor.frame.xaxis * (plate.depth / 2 - column.width)))
                plate.elements = list(anchor.elements)
                self.add_part(plate)
            elif anchor.kind == AnchorKind.AXIS:
                dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
                dowel.transform(Transformation.from_frame(anchor.frame))
                dowel.elements = list(anchor.elements)
                self.add_part(dowel)

    def _bind_triple_beams(self, anchors: list) -> None:
        """Combine :meth:`_bind_double_linear_beams` and :meth:`_bind_double_angled_beams`.

        Of the three beams, two run straight through the column in opposite directions and share merged plates
        exactly like a linear pair; the third meets the column at an angle to them and gets its own plates like a
        solo beam. Since all three converge on the same corner, both groups use notched :class:`StekoSwordPlate`
        rather than plain :class:`StekoPlate`, with complementary :attr:`StekoSwordPlate.phase` values (the linear
        pair's merged plates vs. the angled beam's own) so their teeth weave past each other there.
        """
        face_anchors = [a for a in anchors if a.kind == AnchorKind.FACE]
        axis_anchors = [a for a in anchors if a.kind == AnchorKind.AXIS]

        for anchor in axis_anchors:
            dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
            dowel.transform(Transformation.from_frame(anchor.frame))
            dowel.elements = list(anchor.elements)
            self.add_part(dowel)

        beams = []
        for anchor in face_anchors:
            beam = anchor.elements[1]
            if beam not in beams:
                beams.append(beam)

        # find the two beams that run straight through the column in opposite directions: their anchors' own
        # xaxis (== each beam's own direction, see `_bind_face_and_axis_anchors`) point oppositely.
        linear_pair = None
        for i in range(len(beams)):
            for j in range(i + 1, len(beams)):
                anchor_i = next(a for a in face_anchors if a.elements[1] is beams[i])
                anchor_j = next(a for a in face_anchors if a.elements[1] is beams[j])
                if TOL.is_close(anchor_i.frame.xaxis.dot(anchor_j.frame.xaxis), -1.0):
                    linear_pair = (beams[i], beams[j])
        if linear_pair is None:
            raise ValueError("StekoFastener could not find a linear pair of beams among the three connected to the column.")
        angled_beam = next(beam for beam in beams if beam not in linear_pair)

        # merge the linear pair's plates, as in `_bind_double_linear_beams`, but notched (phase=0)
        self._merge_linear_pair(face_anchors, *linear_pair, phase=0)

        # the angled beam gets its own plates, as in `_bind_solo_beam`, notched with the complementary phase (1)
        for anchor in face_anchors:
            if anchor.elements[1] is not angled_beam:
                continue
            column = anchor.elements[0]
            beam = anchor.elements[1]

            plate = StekoSwordPlate(length=beam.height, depth=self.plate_depth, slot_depth=0.3, thickness=self.plate_thickness, phase=1)
            plate.transform(Transformation.from_frame(anchor.frame))
            plate.transform(Translation.from_vector(anchor.frame.xaxis * (plate.depth / 2 - column.width)))
            plate.elements = list(anchor.elements)
            self.add_part(plate)

    def _bind_quadruple_beams(self, anchors: list) -> None:
        """Combine two :meth:`_bind_double_linear_beams`-style merges: a "+" of two beam pairs, each running
        straight through the column in opposite directions, crossing each other at 90°. Both pairs use notched
        :class:`StekoSwordPlate` with complementary :attr:`StekoSwordPlate.phase` values (0 and 1) so their teeth
        weave past each other at the shared corner, exactly as in :meth:`_bind_double_angled_beams`.
        """
        face_anchors = [a for a in anchors if a.kind == AnchorKind.FACE]
        axis_anchors = [a for a in anchors if a.kind == AnchorKind.AXIS]

        for anchor in axis_anchors:
            dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
            dowel.transform(Transformation.from_frame(anchor.frame))
            dowel.elements = list(anchor.elements)
            self.add_part(dowel)

        beams = []
        for anchor in face_anchors:
            beam = anchor.elements[1]
            if beam not in beams:
                beams.append(beam)

        # pair up beams that run straight through the column in opposite directions
        unpaired = list(beams)
        pairs = []
        while unpaired:
            beam_a = unpaired.pop(0)
            anchor_a = next(a for a in face_anchors if a.elements[1] is beam_a)
            match_index = next(
                (
                    i
                    for i, beam_b in enumerate(unpaired)
                    if TOL.is_close(anchor_a.frame.xaxis.dot(next(a for a in face_anchors if a.elements[1] is beam_b).frame.xaxis), -1.0)
                ),
                None,
            )
            if match_index is None:
                raise ValueError("StekoFastener could not find two linear pairs of beams among the four connected to the column.")
            pairs.append((beam_a, unpaired.pop(match_index)))

        for phase, (beam_a, beam_b) in enumerate(pairs):
            self._merge_linear_pair(face_anchors, beam_a, beam_b, phase=phase)

    def _merge_linear_pair(self, face_anchors: list, beam_a, beam_b, phase: int) -> None:
        """Merge a pair of beams that run straight through the column in opposite directions into notched
        :class:`StekoSwordPlate` plates spanning both, as in :meth:`_bind_double_linear_beams` but with a shank at
        each end (``double_shank=True``) and a comb only in the middle (see :attr:`StekoSwordPlate.phase`) so they
        can weave past another beam's plates converging on the same corner.
        """
        fronts = [a for a in face_anchors if a.role == "slot_front" and a.elements[1] in (beam_a, beam_b)]
        backs = [a for a in face_anchors if a.role == "slot_back" and a.elements[1] in (beam_a, beam_b)]
        for anchor_a, anchor_b in zip(fronts, reversed(backs)):
            column = anchor_a.elements[0]
            beam_x = anchor_a.elements[1]
            beam_y = anchor_b.elements[1]

            plate = StekoSwordPlate(
                length=beam_x.height,
                depth=0.300 + 0.300 + 0.24,
                slot_depth=0.300,
                thickness=self.plate_thickness,
                shank_length=0.300,
                double_shank=True,
                phase=phase,
            )
            plate.transform(Transformation.from_frame(anchor_a.frame))
            plate.transform(Translation.from_vector(anchor_a.frame.xaxis * -(column.width / 2)))
            plate.elements = [column, beam_x, beam_y]
            self.add_part(plate)
