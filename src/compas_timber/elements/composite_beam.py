from .beam import Beam
from compas_timber.base import TimberElement

def _aabb_bounds(points) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _point_box_distance(point, box) -> float:
    box_min, box_max = _aabb_bounds(box.points)
    dx = max(box_min[0] - point[0], 0.0, point[0] - box_max[0])
    dy = max(box_min[1] - point[1], 0.0, point[1] - box_max[1])
    dz = max(box_min[2] - point[2], 0.0, point[2] - box_max[2])
    return (dx * dx + dy * dy + dz * dz) ** 0.5


class CompositeBeam(Beam):
    """A beam that is also a container for other elements.

    A ``CompositeBeam`` behaves exactly like a plain :class:`~compas_timber.elements.Beam` towards
    the rest of a model - it can be extended/cut by ordinary joints just like any beam - while also
    owning a set of child elements (:class:`~compas_timber.elements.Beam`, :class:`~compas_timber.elements.Plate`,
    or any other :class:`~compas_timber.base.TimberElement`) with their own, independently fabricable
    geometry. Children can be arranged however the assembler likes - contiguous segments of a spliced
    beam, the chords/webs of a truss, layers of a built-up cross-section, etc. - there is no assumption
    that they form a single axis.

    Important: once added via :meth:`add_part`, a child's own ``frame`` is interpreted relative to
    *this* composite's frame (exactly like any other parent/child pair in the model tree), not in
    world coordinates - this only goes unnoticed when the composite's own frame happens to be the
    world identity. If you have a part's frame worked out in world coordinates, convert it first,
    e.g. ``composite.frame.to_local_coordinates(part_frame_in_world)``.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The frame representing this composite beam's local coordinate system.
    length : float
        Nominal length of the composite beam.
    width : float
        Nominal width of the composite beam's cross-section.
    height : float
        Nominal height of the composite beam's cross-section.
    cut_all_parts : bool, optional
        If ``False`` (default), a joint that targets this composite is routed to whichever single
        part its location falls in - the right choice when parts are scattered (a spliced beam's
        segments, a truss's members). If ``True``, such a joint is instead applied to *every* part,
        paired by matching index against the other side's parts (or against a single plain element,
        repeated for each part) - the right choice for a layered/built-up cross-section where every
        layer needs the same corner treatment. Parts for which the joint type doesn't apply (e.g. a
        ``Plate`` layer paired with a ``Beam``-oriented joint) are silently skipped.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    parts : list[:class:`~compas_timber.base.TimberElement`]
        The elements contained in this composite beam.
    cut_all_parts : bool
        See ``cut_all_parts`` parameter above.

    """

    def __init__(self, frame, length, width, height, cut_all_parts=False, **kwargs):
        super(CompositeBeam, self).__init__(frame, length, width, height, **kwargs)
        self._parts = []
        self.cut_all_parts = cut_all_parts

    def __repr__(self) -> str:
        return "CompositeBeam(frame={!r}, length={}, width={}, height={}, parts={})".format(self.frame, self.length, self.width, self.height, len(self.parts))

    @property
    def is_group_element(self):
        return True

    @property
    def parts(self) -> list:
        """The elements contained in this composite beam."""
        if self.model is not None:
            return list(self.children)
        return self._parts

    def add_part(self, element) -> None:
        """Adds a child element to this composite beam.

        Elements can be added in any arrangement - there is no assumption of a contiguous
        ordering along a single axis. Position/orientation is entirely up to the element itself.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element (e.g. a :class:`~compas_timber.elements.Beam` or :class:`~compas_timber.elements.Plate`)
            to add as a part of this composite beam.

        """
        self._parts.append(element)

    def merge_contained_elements(self, model) -> None:
        """Adds this composite beam's parts to *model* as children of this element.

        Parts already present in *model* are left untouched, so this can be called incrementally
        as parts are constructed and added.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model this composite beam has already been added to.

        """
        for part in self._parts:
            if part not in model.elements():
                model.add_element(part, parent=self)

    def resolve_part_at(self, point) -> TimberElement:
        """Returns the part of this composite beam closest to (or containing) *point*.

        Used to route a joint that targets this composite beam to whichever of its real parts the
        joint's :attr:`~compas_timber.connections.Joint.location` actually applies to - see
        :meth:`~compas_timber.connections.Joint.resolve_composite_elements`.

        Parameters
        ----------
        point : :class:`~compas.geometry.Point`
            World-space point - typically a joint's estimated interaction location.

        Returns
        -------
        :class:`~compas_timber.base.TimberElement`

        Raises
        ------
        ValueError
            If this composite beam has no parts.

        """
        if not self.parts:
            raise ValueError("{!r} has no parts to resolve.".format(self))
        return min(self.parts, key=lambda part: _point_box_distance(point, part.aabb))
