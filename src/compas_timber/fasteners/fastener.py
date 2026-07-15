from __future__ import annotations

from typing import Optional

from compas.geometry import Frame
from compas.geometry import Transformation
from compas_model.elements import Element


class FastenerPart(Element):
    """Base class for the parts that make up a :class:`~compas_timber.elements.Fastener`.

    A part is a non-timber :class:`~compas_model.elements.Element`. In a model it lives as a child of the fastener that
    orchestrates it (``fastener.children``), and its placement in the model is expressed by the element
    ``transformation`` rather than a stored frame. Besides carrying its own geometry, a part may emit fabrication
    features onto the timber elements its fastener connects (see :meth:`apply_fastening_features`).

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`, optional
        The placement frame of the part. Stored as the element ``transformation``. Defaults to the world XY frame.

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


class Fastener(Element):
    """A connector element (screws, dowels, plates, ...) joining two or more timber elements.

    A fastener is a non-timber :class:`~compas_model.elements.Element` that acts as a container: it orchestrates the
    creation of its :class:`~compas_timber.elements.FastenerPart` parts and, once added to a model, holds them as its
    children in the model tree (``fastener.children``). The fastener itself has no geometry of its own; its geometry is
    the aggregation of its parts.

    Before the fastener is added to a model, parts are staged with :meth:`add_part`. When the model adds the fastener it
    moves the staged parts into the tree as children (``model.add_element(part, parent=fastener)``).

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`, optional
        The placement frame of the fastener. Stored as the element ``transformation``. Defaults to the world XY frame.

    Attributes
    ----------
    parts : list[:class:`~compas_timber.elements.FastenerPart`]
        The parts that make up the fastener. Once the fastener is in a model these are its children; before that, the
        staged parts.
    geometry : list
        The geometry of the fastener, i.e. the geometry of each of its parts in model coordinates.
    """

    @property
    def __data__(self):
        return {"frame": self.placement_frame, "name": self.name}

    def __init__(self, frame: Optional[Frame] = None, **kwargs):
        transformation = Transformation.from_frame(frame) if frame is not None else None
        super().__init__(transformation=transformation, **kwargs)
        self._parts = []  # staging area for parts before the fastener is added to a model

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

    @property
    def parts(self):
        """The parts of the fastener: its children once in a model, otherwise the staged parts."""
        if self.model is not None:
            return self.children
        return self._parts

    def add_part(self, part) -> None:
        """Stage a part to be added to the model as a child of this fastener.

        Parameters
        ----------
        part : :class:`~compas_timber.elements.FastenerPart`
            The part to add to the fastener.
        """
        self._parts.append(part)

    def compute_elementgeometry(self, include_features: bool = False):
        """A fastener has no geometry of its own; its geometry comes from its parts."""
        return None

    @property
    def geometry(self):
        """The geometry of the fastener, i.e. the geometry of each of its parts in model coordinates."""
        geometries = []
        for part in self.parts:
            part_geometry = part.geometry
            if isinstance(part_geometry, (list, tuple)):
                geometries.extend(part_geometry)
            else:
                geometries.append(part_geometry)
        return geometries

    def apply_fastening_features(self, elements: list) -> None:
        """Apply the fabrication features generated by the parts to the connected timber elements.

        Parameters
        ----------
        elements : list[:class:`~compas_model.elements.Element`]
            The timber elements connected by this fastener.
        """
        for part in self.parts:
            part.apply_fastening_features(elements)
