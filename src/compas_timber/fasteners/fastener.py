from __future__ import annotations

from typing import List
from typing import Optional

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation
from compas_model.elements import Element


class FastenerPart(Element):
    """Base class for the parts that make up a :class:`~compas_timber.elements.Fastener`.

    A part is a non-timber :class:`~compas_model.elements.Element`. In a model it lives as a child of its parent (the
    fastener, or another part) in the model tree, and its placement is expressed by the element ``transformation``
    relative to that parent rather than a stored world frame. A part may itself own child parts, so a fastener's
    anatomy can be a *tree* rather than a flat list (e.g. a ball node owns a core, the core owns rods, each rod owns a
    plate) - :attr:`parts` exposes the direct children and :attr:`all_parts` walks the whole subtree. Besides
    carrying its own geometry, a part may emit fabrication features onto the timber elements its fastener connects
    (see :meth:`apply_fastening_features`).

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

    def __init__(self, frame: Optional[Frame] = None, element_guids: Optional[List[str]] = None, **kwargs):
        transformation = Transformation.from_frame(frame) if frame is not None else None
        super().__init__(transformation=transformation, **kwargs)
        self._parts = []  # staging area for child parts before this part is added to a model
        # the elements this part actually applies to (as opposed to every element the fastener as a whole connects),
        # set by the fastener's `bind()` from the anchor's `elements`; restored from `element_guids` after model
        # deserialization, since elements aren't available yet when the part itself is reconstructed
        self.elements = []
        self._element_guids = tuple(element_guids) if element_guids else ()
        # the fabrication features this part has added to `elements` via `apply_fastening_features()` (e.g. a
        # plate's recess Pocket, a dowel's Drilling) - mirrors `Joint.features`, so a viewer can show/hide just
        # the features a specific fastener part is responsible for. Not called `features` - `Element` (this
        # class's base) already reserves that name for the part's *own* features.
        self.applied_features = []

    @property
    def parts(self) -> List["FastenerPart"]:
        """The direct child parts: the model-tree children once in a model, otherwise the staged parts."""
        if self.model is not None:
            return list(self.children)
        return self._parts

    @property
    def all_parts(self) -> List["FastenerPart"]:
        """All descendant parts of this part, depth-first (children, grandchildren, ...)."""
        collected = []
        for part in self.parts:
            collected.append(part)
            collected.extend(part.all_parts)
        return collected

    def add_part(self, part: "FastenerPart") -> "FastenerPart":
        """Stage a part as a direct child of this part.

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

    @property
    def placement_frame(self) -> Frame:
        """The placement frame of the part relative to its parent, derived from its transformation."""
        if self.transformation is None:
            return Frame.worldXY()
        return Frame.from_transformation(self.transformation)

    @property
    def element_guids(self) -> List[str]:
        """The guids of the elements this part applies to, for serialization."""
        if self.elements:
            return [str(element.guid) for element in self.elements]
        return list(self._element_guids)

    def restore_elements_from_keys(self, model) -> None:
        """Restore the reference to the elements this part applies to, after model deserialization.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model the elements belong to.
        """
        if self._element_guids:
            self.elements = [model[guid] for guid in self._element_guids]

    def compute_modeltransformation(self) -> Transformation:
        """Same as the base implementation but also works for a standalone (model-less) part."""
        if not self.model:
            return self.transformation or Transformation()
        return super().compute_modeltransformation()

    @property
    def geometry(self):
        """The geometry of the part in model coordinates."""
        return self.elementgeometry.transformed(self.modeltransformation)

    def apply_fastening_features(self) -> None:
        """Emit fabrication features onto :attr:`elements`, the host timber elements this part applies to.

        The default does nothing. Parts that machine their hosts (e.g. a plate cutting a recess) override this.
        """
        pass


class Fastener(Element):
    """A connector element (screws, dowels, plates, ...) joining two or more timber elements.

    A fastener is a non-timber :class:`~compas_model.elements.Element` that acts as a container: it holds the
    :class:`~compas_timber.elements.FastenerPart` parts that make up its physical anatomy, once in a model, in the
    model tree. The parts may form a nested hierarchy (a part can own child parts); the fastener itself has no
    geometry of its own, its geometry is the aggregation of the whole part subtree.

    A ``Fastener`` is the *resolved*, model-ready element: it represents one specific occurrence of a fastener at one
    place in the model, built either directly (staging parts with :meth:`add_part`, e.g. for a custom
    :class:`~compas_timber.elements.GeometryPart`-based fastener) or by a :class:`~compas_timber.fasteners.FastenerSystem`'s
    :meth:`~compas_timber.fasteners.FastenerSystem.bind`, which returns a fresh ``Fastener`` per call. Before the
    fastener is added to a model, parts are staged in a plain list; when the model adds the fastener it moves the
    staged subtree into the tree (``model.add_element(part, parent=...)``).

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
        self._parts = []  # staging area for child parts before this fastener is added to a model

    @property
    def parts(self) -> List["FastenerPart"]:
        """The direct child parts: the model-tree children once in a model, otherwise the staged parts."""
        if self.model is not None:
            return list(self.children)
        return self._parts

    @property
    def all_parts(self) -> List["FastenerPart"]:
        """All descendant parts of this fastener, depth-first (children, grandchildren, ...)."""
        collected = []
        for part in self.parts:
            collected.append(part)
            collected.extend(part.all_parts)
        return collected

    def add_part(self, part: "FastenerPart") -> "FastenerPart":
        """Stage a part as a direct child of this fastener.

        The part is held in a staging area until the fastener is added to a model, at which point the model moves
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

    def apply_fastening_features(self) -> None:
        """Apply the fabrication features generated by the parts to the elements each part applies to.

        Every part in the subtree is given the chance to machine the elements referenced by its own :attr:`FastenerPart.elements`
        (set during binding), rather than every element this fastener connects as a whole.
        """
        for part in self.all_parts:
            part.apply_fastening_features()


class FastenerSystem(Data):
    """The design-time recipe for a fastener: what a fastener designer authors and reuses across joints.

    A system is joint-agnostic: it declares the kind(s) of :class:`~compas_timber.fasteners.FastenerAnchor` it
    consumes (:attr:`ACCEPTS`) and knows how to build a fastener's parts from a set of anchors of that kind. It is
    plain data - not a :class:`~compas_model.elements.Element` - so it carries no guid and is never itself added to a
    model; it can be authored once and bound to as many joints as needed.

    :meth:`bind` is a pure factory: given a set of anchors, it returns a brand-new, fully-built
    :class:`~compas_timber.elements.Fastener` ready to be passed to
    :meth:`~compas_timber.model.TimberModel.add_fastener`. It never mutates the system itself, so the same system
    instance can be bound to multiple joints independently, and mutating it afterwards cannot retroactively affect a
    fastener it already produced.

    Attributes
    ----------
    ACCEPTS : list[:class:`~compas_timber.fasteners.AnchorKind`]
        The kinds of anchor this system binds to. Set by subclasses.
    """

    ACCEPTS: List = []

    def _validate_anchors(self, anchors: list) -> list:
        """Check that every anchor is of a kind this system accepts, returning them as a list.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors to validate.

        Returns
        -------
        list of :class:`~compas_timber.fasteners.FastenerAnchor`

        Raises
        ------
        ValueError
            If any of the anchors are not of a kind this system accepts.
        """
        anchors = list(anchors)
        wrong = [anchor for anchor in anchors if anchor.kind not in self.ACCEPTS]
        if wrong:
            raise ValueError("{} accepts {} anchors, got {}.".format(type(self).__name__, self.ACCEPTS, [anchor.kind for anchor in wrong]))
        return anchors

    def bind(self, anchors: list) -> "Fastener":
        """Build a fastener from this system's recipe, placed at the given anchors.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors to place the fastener's parts at. Every anchor must be of a kind this system accepts.

        Returns
        -------
        :class:`~compas_timber.elements.Fastener`
            A new fastener, its parts staged and positioned, ready to be added to a model.
        """
        raise NotImplementedError
