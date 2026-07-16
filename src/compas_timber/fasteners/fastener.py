from __future__ import annotations

from typing import List
from typing import Optional

from compas.geometry import Frame
from compas.geometry import Transformation
from compas_model.elements import Element


class PartContainer:
    """Mixin adding nested part staging and subtree traversal to fastener elements.

    Both :class:`Fastener` and :class:`FastenerPart` can own child parts, so a fastener's anatomy can be a *tree* rather
    than a flat list (e.g. a ball node owns a core, the core owns rods, each rod owns a plate). Before the owning element
    is added to a model, children are staged in a plain list; once in the model they live in the model tree as
    ``children``. Either way, :attr:`parts` exposes the direct children and :attr:`all_parts` walks the whole subtree.

    The placement of every part is expressed by its element ``transformation`` *relative to its parent*; the model tree
    composes those into each part's ``modeltransformation``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parts = []  # staging area for child parts before this element is added to a model

    @property
    def parts(self) -> List["FastenerPart"]:
        """The direct child parts: the model-tree children once in a model, otherwise the staged parts."""
        if self.model is not None:
            return list(self.children)
        return self._parts

    @property
    def all_parts(self) -> List["FastenerPart"]:
        """All descendant parts of this element, depth-first (children, grandchildren, ...)."""
        collected = []
        for part in self.parts:
            collected.append(part)
            collected.extend(part.all_parts)
        return collected

    def add_part(self, part: "FastenerPart") -> "FastenerPart":
        """Stage a part as a direct child of this element.

        The part is held in a staging area until the owning fastener is added to a model, at which point the model moves
        the whole staged subtree into the tree (``model.add_element(part, parent=this)``).

        Parameters
        ----------
        part : :class:`~compas_timber.elements.FastenerPart`
            The part to stage as a child.

        Returns
        -------
        :class:`~compas_timber.elements.FastenerPart`
            The added part, for chaining.
        """
        self._parts.append(part)
        return part


class FastenerPart(PartContainer, Element):
    """Base class for the parts that make up a :class:`~compas_timber.elements.Fastener`.

    A part is a non-timber :class:`~compas_model.elements.Element`. In a model it lives as a child of its parent (the
    fastener, or another part) in the model tree, and its placement is expressed by the element ``transformation``
    relative to that parent rather than a stored world frame. A part may itself own child parts (see
    :class:`PartContainer`). Besides carrying its own geometry, a part may emit fabrication features onto the timber
    elements its fastener connects (see :meth:`apply_fastening_features`).

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`, optional
        The placement frame of the part relative to its parent. Stored as the element ``transformation``. Defaults to the
        world XY frame (identity relative to the parent).

    Notes
    -----
    This replaces the former ``Part`` abstract base class. Containment, identity, serialization and transformation are
    all inherited from :class:`~compas_model.elements.Element`.
    """

    def __init__(self, frame: Optional[Frame] = None, **kwargs):
        transformation = Transformation.from_frame(frame) if frame is not None else None
        super().__init__(transformation=transformation, **kwargs)

    @property
    def placement_frame(self) -> Frame:
        """The placement frame of the part relative to its parent, derived from its transformation."""
        if self.transformation is None:
            return Frame.worldXY()
        return Frame.from_transformation(self.transformation)

    def compute_modeltransformation(self) -> Transformation:
        """Same as the base implementation but also works for a standalone (model-less) part."""
        if not self.model:
            return self.transformation or Transformation()
        return super().compute_modeltransformation()

    @property
    def geometry(self):
        """The geometry of the part in model coordinates."""
        return self.elementgeometry.transformed(self.modeltransformation)

    def apply_fastening_features(self, elements: list) -> None:
        """Emit fabrication features onto the host timber elements.

        The default does nothing. Parts that machine their hosts (e.g. a plate cutting a recess) override this.

        Parameters
        ----------
        elements : list[:class:`~compas_model.elements.Element`]
            The timber elements connected by the fastener this part belongs to.
        """
        pass


class Fastener(PartContainer, Element):
    """A connector element (screws, dowels, plates, ...) joining two or more timber elements.

    A fastener is a non-timber :class:`~compas_model.elements.Element` that acts as a container: it orchestrates the
    creation of its :class:`~compas_timber.elements.FastenerPart` parts and, once added to a model, holds them in the
    model tree. The parts may form a nested hierarchy (see :class:`PartContainer`); the fastener itself has no geometry
    of its own, its geometry is the aggregation of the whole part subtree.

    Before the fastener is added to a model, parts are staged with :meth:`add_part`. When the model adds the fastener it
    moves the staged subtree into the tree (``model.add_element(part, parent=...)``).

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`, optional
        The placement frame of the fastener. Stored as the element ``transformation``. Defaults to the world XY frame.

    Attributes
    ----------
    parts : list[:class:`~compas_timber.elements.FastenerPart`]
        The direct child parts of the fastener (its tree children once in a model, otherwise the staged parts).
    all_parts : list[:class:`~compas_timber.elements.FastenerPart`]
        Every part in the fastener's subtree.
    geometry : list
        The geometry of the fastener, i.e. the geometry of every part in its subtree in model coordinates.
    """

    @property
    def __data__(self):
        return {"frame": self.placement_frame, "name": self.name}

    def __init__(self, frame: Optional[Frame] = None, **kwargs):
        transformation = Transformation.from_frame(frame) if frame is not None else None
        super().__init__(transformation=transformation, **kwargs)

    @property
    def placement_frame(self) -> Frame:
        """The placement frame of the fastener relative to its parent, derived from its transformation."""
        if self.transformation is None:
            return Frame.worldXY()
        return Frame.from_transformation(self.transformation)

    def compute_modeltransformation(self) -> Transformation:
        """Same as the base implementation but also works for a standalone (model-less) fastener."""
        if not self.model:
            return self.transformation or Transformation()
        return super().compute_modeltransformation()

    def compute_elementgeometry(self, include_features: bool = False):
        """A fastener has no geometry of its own; its geometry comes from its parts."""
        return None

    @property
    def geometry(self):
        """The geometry of the fastener, i.e. the geometry of every part in its subtree in model coordinates."""
        geometries = []
        for part in self.all_parts:
            part_geometry = part.geometry
            if isinstance(part_geometry, (list, tuple)):
                geometries.extend(part_geometry)
            else:
                geometries.append(part_geometry)
        return geometries

    def apply_fastening_features(self, elements: list) -> None:
        """Apply the fabrication features generated by the parts to the connected timber elements.

        Every part in the subtree is given the chance to machine the connected elements.

        Parameters
        ----------
        elements : list[:class:`~compas_model.elements.Element`]
            The timber elements connected by this fastener.
        """
        for part in self.all_parts:
            part.apply_fastening_features(elements)
