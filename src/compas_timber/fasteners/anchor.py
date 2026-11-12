from __future__ import annotations

from enum import Enum
from typing import Optional

from compas.geometry import Frame


class AnchorKind(Enum):
    """The geometric primitive a fastener anchor affords.

    This is the small, stable vocabulary that fasteners bind against. A joint maps its anatomy onto these kinds; a
    fastener declares which kind it consumes. Because the kind is joint-agnostic, a fastener written against ``FACE``
    works on any joint that publishes ``FACE`` anchors.
    """

    POINT = 0  # a 0-D anchor, e.g. a ball node
    AXIS = 1  # a 1-D line, e.g. a rod, dowel or screw
    FACE = 2  # a 2-D plane, e.g. a plate or gusset
    VOLUME = 3  # a 3-D region, e.g. a glued in-fill block


class FastenerAnchor:
    """A single place on a joint where a fastener may attach.

    An anchor describes the *anatomy* of the joint, not the placement of any particular fastener. It is published by the
    joint and consumed by the fastener.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate frame of the anchor, expressed in the coordinate system shared by the joined elements.
    kind : :class:`~compas_timber.fasteners.AnchorKind`
        The geometric primitive this anchor affords.
    elements : list
        The timber elements this anchor references, i.e. the elements a fastener bound here would reference and cut.
    ref_side_index : int, optional
        The BTLx ref_side index this anchor is anchored to, when applicable (kind ``FACE``). Passing it through spares
        the fastener from re-deriving it.
    role : str, optional
        An optional joint-specific tag (e.g. ``"side_face"``), for human readability and fine selection. Not part of the
        stable contract.

    Attributes
    ----------
    normal : :class:`~compas.geometry.Vector`
        The z-axis of the anchor frame, used to break symmetry between otherwise equivalent anchors.
    """

    def __init__(self, frame: Frame, kind: AnchorKind, elements: list, ref_side_index: Optional[int] = None, role: Optional[str] = None):
        self.frame = frame
        self.kind = kind
        self.elements = elements
        self.ref_side_index = ref_side_index
        self.role = role

    def __repr__(self):
        return "FastenerAnchor(kind={}, role={}, ref_side_index={})".format(self.kind, self.role, self.ref_side_index)

    @property
    def normal(self):
        return self.frame.zaxis


class FastenerAnchors(list):
    """A queryable collection of :class:`~compas_timber.fasteners.FastenerAnchor`.

    Selection is done by typed query rather than by index, so it stays readable and stable as joints publish more
    anchors.
    """

    def of_kind(self, kind: AnchorKind) -> "FastenerAnchors":
        """Return the anchors of the given kind."""
        return FastenerAnchors(anchor for anchor in self if anchor.kind is kind)

    def referencing(self, element) -> "FastenerAnchors":
        """Return the anchors that reference the given element."""
        return FastenerAnchors(anchor for anchor in self if element in anchor.elements)

    def with_role(self, role: str) -> "FastenerAnchors":
        """Return the anchors carrying the given joint-specific role."""
        return FastenerAnchors(anchor for anchor in self if anchor.role == role)
