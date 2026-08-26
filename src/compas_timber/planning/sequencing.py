"""Adapter between :class:`~compas_timber.model.TimberModel` and ``assembly_sequencing``.

This is the only place the two packages meet. Constraint *computation* stays on the joint
classes, where the joint's private geometry lives; only *consumption* moves across. The
adapter's job is to flatten a model into a
:class:`~assembly_sequencing.boundary.SequencingInput` and to write a
:class:`~assembly_sequencing.result.SequenceResult` back onto the model.

Two facts worth stating out loud, because both are limitations a user will meet:

* **Beams only.** Plates, panels, fasteners and group containers are excluded and reported
  as such. Sequencing them would need a different notion of insertion than "slide a stick
  along a vector", and giving them a height of zero -- which sinks them to the bottom of
  the ranking while looking like a real measurement -- is worse than leaving them out and
  saying so.
* **Excluded elements are invisible to the joint kinematics** but are still treated as
  present by the swept broad-phase check, which is the conservative reading.

"""

from compas.geometry import Line
from compas.geometry import Vector

from assembly_sequencing import APPROACH_DISTANCE
from assembly_sequencing import HalfSpace
from assembly_sequencing import SequencingInput
from assembly_sequencing import SignedAxis
from assembly_sequencing import generate as generate_sequence
from compas_timber.connections import Joint

MANUAL_ATTRIBUTE = "requires_manual_assembly"
"""str: Element attribute holding the hand-placement flag.

Hand placement is a fact about the design, so it lives on the element and is serialized
with the model. Pinned order is a fact about a particular build and is supplied per run.
"""

SEQUENCE_ATTRIBUTE = "assembly_sequence"
VECTOR_ATTRIBUTE = "insertion_vector"
STATE_ATTRIBUTE = "extraction_state"

_SWEEP_START_FRACTION = 0.05

_DEGENERATE_AXIS = 1e-6
"""float: Below this a candidate separating axis from a cross product is discarded.

The cross of two unit vectors has the magnitude of the sine of the angle between them, so
this is about two thousandths of a degree.
"""


def _element_id(element):
    return str(element.guid)


def _uses_generic_fallback(joint):
    """Whether this joint inherits the permissive base implementation.

    The base :meth:`~compas_timber.connections.Joint.get_kinematic_constraint` returns a
    single half-space pointing roughly beam-to-beam, which almost always yields a valid
    extraction. A large fraction of the joint library still relies on it, and nothing else
    distinguishes "computed" from "nobody implemented this joint". Constraints from the
    fallback are tagged so results can report how much of the answer was a guess.

    """
    return type(joint).get_kinematic_constraint is Joint.get_kinematic_constraint


def constraints_from_joint_output(raw, inferred=False):
    """Convert what a joint returns into typed constraints.

    Parameters
    ----------
    raw : :class:`compas.geometry.Line` or :class:`compas.geometry.Vector` or list
        A ``Line`` is a signed 1-DOF axis, oriented ``start`` -> ``end``. A ``Vector`` is
        the inward normal of a permitted half-space. A list or tuple is any mixture of the
        two.
    inferred : bool, optional
        Tag the results as having come from the generic fallback.

    Returns
    -------
    list of :class:`~assembly_sequencing.constraints.Constraint`

    Raises
    ------
    TypeError
        On anything else -- including the ``Plane`` that four docstrings in this package
        used to promise but no implementation ever returned. Silently dropping an
        unrecognised constraint makes an element look *more* free than it is.

    """
    if isinstance(raw, Line):
        return [SignedAxis.from_line(raw, inferred=inferred)]
    if isinstance(raw, Vector):
        return [HalfSpace(raw, inferred=inferred)]
    if isinstance(raw, (list, tuple)):
        constraints = []
        for item in raw:
            constraints.extend(constraints_from_joint_output(item, inferred=inferred))
        return constraints
    raise TypeError(
        "Cannot interpret {!r} as a kinematic constraint. Expected a Line (signed 1-DOF axis), a Vector (half-space normal), or a list of those.".format(type(raw).__name__)
    )


def _swept_aabb(box, direction, distance):
    """Axis-aligned bounds of an oriented box swept along `direction`.

    The sweep starts a little way along the direction rather than at the box itself, so
    that elements already in contact at the start position do not veto every extraction.

    """
    corners = box.points
    near = distance * _SWEEP_START_FRACTION
    xs = []
    ys = []
    zs = []
    for scale in (near, distance):
        for corner in corners:
            xs.append(corner[0] + direction.x * scale)
            ys.append(corner[1] + direction.y * scale)
            zs.append(corner[2] + direction.z * scale)
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _box_bounds(box):
    corners = box.points
    xs = [corner[0] for corner in corners]
    ys = [corner[1] for corner in corners]
    zs = [corner[2] for corner in corners]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _bounds_overlap(a, b, tolerance=1e-6):
    return (
        a[0] <= b[3] - tolerance and b[0] <= a[3] - tolerance and a[1] <= b[4] - tolerance and b[1] <= a[4] - tolerance and a[2] <= b[5] - tolerance and b[2] <= a[5] - tolerance
    )


def _box_frame(box):
    """An oriented box as ``(centre, [axis, ...], [half_extent, ...])`` in world space."""
    frame = box.frame
    centre = (frame.point.x, frame.point.y, frame.point.z)
    axes = [(frame.xaxis.x, frame.xaxis.y, frame.xaxis.z), (frame.yaxis.x, frame.yaxis.y, frame.yaxis.z), (frame.zaxis.x, frame.zaxis.y, frame.zaxis.z)]
    extents = [box.xsize / 2.0, box.ysize / 2.0, box.zsize / 2.0]
    return centre, axes, extents


def _norm(vector):
    return (vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2) ** 0.5


def _unit(vector):
    length = _norm(vector)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _radius(axes, extents, normal):
    """Half the width of an oriented box's shadow on `normal`."""
    return sum(abs(_dot(axis, normal)) * extent for axis, extent in zip(axes, extents))


def _separating_axes(axes_a, axes_b, sweep):
    """The finite axis set that decides overlap between a swept box and a static box.

    The two boxes' face normals plus the cross products of their edge directions, which is
    the standard box-versus-box set, extended with the cross products of the sweep
    direction against the stationary box's edges -- the axes the sweep adds, since the
    swept solid's extra edges all run along it.

    Near-parallel edges give a cross product that is all rounding error; those are dropped.
    Dropping an axis is the safe direction, because one axis fewer can only make the test
    report an overlap, and the face normals already cover what it stood for.

    """
    axes = list(axes_a) + list(axes_b)
    for axis_a in axes_a:
        for axis_b in axes_b:
            axes.append(_cross(axis_a, axis_b))
    for axis_b in axes_b:
        axes.append(_cross(sweep, axis_b))
    return [_unit(axis) for axis in axes if _norm(axis) >= _DEGENERATE_AXIS]


def _separation(offset, axes, axes_a, extents_a, axes_b, extents_b):
    """How far apart two oriented boxes are, along their worst-case separating axis.

    Positive is a gap, negative is interpenetration and its magnitude is the depth. This is
    the separating axis theorem read as a quantity rather than a yes or no: the boxes are
    disjoint exactly when some axis reports a gap, so the largest value over the axis set
    is the answer.

    Parameters
    ----------
    offset : tuple
        The second box's centre relative to the first's.
    axes : list
        The candidate separating axes, already unitized, from :func:`_separating_axes`.
    axes_a, extents_a, axes_b, extents_b : list
        The two boxes' frames, from :func:`_box_frame`.

    Returns
    -------
    float

    """
    worst = None
    for normal in axes:
        gap = abs(_dot(offset, normal)) - _radius(axes_a, extents_a, normal) - _radius(axes_b, extents_b, normal)
        if worst is None or gap > worst:
            worst = gap
    return 0.0 if worst is None else worst


def _swept_box_hits_box(moving, direction, near, far, other, tolerance=1e-6):
    """Whether sweeping an oriented box along `direction` runs it into another oriented box.

    Two questions, because the boxes may already be touching before anything moves.

    **Already in contact.** Then the contact is a fact about the assembled model, not about
    the path, and the only thing worth asking is whether this direction makes it worse. The
    box is swept to `far` and the interpenetration is measured again: deeper means the
    direction drives the element further into something it is already up against, and that
    is an obstruction; the same or shallower means the direction is a way out, and vetoing
    it would have the element veto itself.

    That case is not an edge case in timber. Beams in a reciprocal frame lap and bear on
    one another, and the model records a joint only for the pairs that were explicitly
    connected -- in the frame this was written against, 52 unjointed pairs of beams
    overlapped at rest by a median of 39 mm on a 100 x 140 section. Testing those pairs as
    if the element started clear rejects *every* direction for *every* one of them, and the
    search stops with most of the model still standing. This is the same reasoning that
    already skips jointed neighbours, applied to the contact a joint does not happen to
    describe.

    **Starting clear.** Then the swept solid is the convex hull of the box at `near` and the
    same box at `far`, which is convex, so the separating axis theorem is exact: the two are
    disjoint if and only if one axis in :func:`_separating_axes` separates their
    projections.

    Parameters
    ----------
    moving : :class:`compas.geometry.Box`
    direction : :class:`compas.geometry.Vector`
        Unit sweep direction.
    near : float
        Where the sweep starts, as a distance from the box's own position.
    far : float
        Where the sweep ends.
    other : :class:`compas.geometry.Box`
    tolerance : float, optional
        A gap narrower than this counts as contact rather than clearance, and a change in
        depth smaller than this counts as sliding rather than as driving in deeper.

    Returns
    -------
    bool

    """
    centre_a, axes_a, extents_a = _box_frame(moving)
    centre_b, axes_b, extents_b = _box_frame(other)

    sweep = (direction.x, direction.y, direction.z)
    offset = tuple(centre_b[axis] - centre_a[axis] for axis in range(3))
    axes = _separating_axes(axes_a, axes_b, sweep)

    at_rest = _separation(offset, axes, axes_a, extents_a, axes_b, extents_b)
    if at_rest < 0.0:
        # Moving the box by `far` moves the other box by `-far` in its frame.
        shifted = tuple(offset[axis] - sweep[axis] * far for axis in range(3))
        at_end = _separation(shifted, axes, axes_a, extents_a, axes_b, extents_b)
        return at_end < at_rest - tolerance

    for normal in axes:
        # B's centre, relative to the swept solid's, measured along the axis.
        delta = _dot(offset, normal)
        travel = _dot(sweep, normal)
        reach_low = min(near * travel, far * travel)
        reach_high = max(near * travel, far * travel)
        span = _radius(axes_a, extents_a, normal) + _radius(axes_b, extents_b, normal)

        if max(delta - reach_high, reach_low - delta) > span - tolerance:
            return False

    return True


class TimberModelAdapter(object):
    """Builds a :class:`~assembly_sequencing.boundary.SequencingInput` from a model.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
    use_geometry : bool, optional
        Supply the swept broad-phase callback. Without it the sequencer relies on joint
        constraints alone and can be fooled by an element that is in the way but not
        jointed. Turning it off is useful when element geometry cannot be computed.

    Attributes
    ----------
    elements_by_id : dict
        Maps element id -> element, for every sequenceable element.
    excluded : dict
        Maps element id -> reason, for everything left out.

    """

    def __init__(self, model, use_geometry=True):
        self.model = model
        self.use_geometry = use_geometry
        self.elements_by_id = {}
        self.excluded = {}
        self._excluded_elements = {}
        self._bounds_cache = {}
        self._collect()

    def _collect(self):
        for element in self.model.elements():
            element_id = _element_id(element)
            if getattr(element, "is_group_element", False):
                self.excluded[element_id] = "group containers are not sequenced"
                self._excluded_elements[element_id] = element
            elif getattr(element, "is_beam", False):
                self.elements_by_id[element_id] = element
            else:
                self.excluded[element_id] = "{} elements are not sequenced; beams only, for now".format(type(element).__name__.lower())
                self._excluded_elements[element_id] = element

    def _joints_for(self, element):
        return self.model.get_joints_for_element(element)

    def _neighbors(self):
        neighbors = {element_id: set() for element_id in self.elements_by_id}
        for element_id, element in self.elements_by_id.items():
            for joint in self._joints_for(element):
                for other in joint.elements:
                    other_id = _element_id(other)
                    if other_id != element_id and other_id in self.elements_by_id:
                        neighbors[element_id].add(other_id)
        # Enforce symmetry: a joint recorded on one side only would otherwise be a
        # one-directional constraint, which is not a thing.
        for element_id, others in list(neighbors.items()):
            for other_id in others:
                neighbors[other_id].add(element_id)
        return neighbors

    def _joint_members(self):
        members = {}
        for joint in self.model.joints:
            member_ids = tuple(_element_id(element) for element in joint.elements)
            if any(member_id in self.elements_by_id for member_id in member_ids):
                members[str(joint.guid)] = member_ids
        return members

    def _groups(self):
        groups = {}
        for element in self.model.elements():
            if not getattr(element, "is_group_element", False):
                continue
            label = _element_id(element)
            for child in element.children or ():
                child_id = _element_id(child)
                if child_id in self.elements_by_id:
                    groups[child_id] = label
        return groups

    def constraints(self, element_id, active_neighbor_ids):
        """Gather the constraints on one element from its still-active joints.

        A joint contributes nothing once every other member of it has been removed, which
        is what makes an n-ary joint's contribution depend on the active set rather than on
        the joint alone.

        """
        element = self.elements_by_id[element_id]
        constraints = []
        for joint in self._joints_for(element):
            partners = set(_element_id(other) for other in joint.elements) - {element_id}
            if not partners & set(active_neighbor_ids):
                continue
            raw = joint.get_kinematic_constraint(element)
            constraints.extend(constraints_from_joint_output(raw, inferred=_uses_generic_fallback(joint)))
        return constraints

    def _bounds(self, element_id):
        if element_id not in self._bounds_cache:
            element = self.elements_by_id.get(element_id) or self._excluded_elements[element_id]
            self._bounds_cache[element_id] = _box_bounds(element.obb)
        return self._bounds_cache[element_id]

    def path_is_clear(self, element_id, direction, distance, active_ids):
        """Swept broad-phase against every other element still in place.

        Jointed neighbours are skipped: their interaction with this element is already
        described exactly by the joint constraints, and a beam sliding along a joint face
        would otherwise veto itself. The check exists to catch the elements a joint cannot
        see -- in a dense lattice a beam can be kinematically free per its joints while its
        extraction path passes straight through a beam it is not jointed to.

        Excluded elements are treated as present, which is the conservative reading.

        Two phases. Axis-aligned bounds around the swept box reject the elements that are
        nowhere near, cheaply; whatever survives goes to :func:`_swept_box_hits_box`, which
        is an exact separating-axis test between the swept oriented box and the other
        element's oriented box.

        The narrow phase is not an optimization, it is the answer. Axis-aligned bounds
        around a diagonal brace enclose several times the brace's own volume, nearly all of
        it empty, and the beam whose extraction path crosses that empty corner is reported
        obstructed when nothing is in its way. Erring towards "obstructed" is the safe
        direction for a robot, but only where the obstruction is real: a false veto on the
        highest elements is what drives a bottom-up sequence to give up on them and start
        pulling posts out from under beams that are still standing.

        What remains approximate is the *element*, not the test. An element is taken as its
        oriented bounding box, so a beam is treated as solid to its full section and its
        processings are ignored. That still errs towards "obstructed".

        """
        element = self.elements_by_id[element_id]
        try:
            box = element.obb
            swept = _swept_aabb(box, direction, distance)
        except Exception:  # geometry unavailable, e.g. an element without a blank
            return True

        near = distance * _SWEEP_START_FRACTION
        neighbor_ids = set(_element_id(other) for joint in self._joints_for(element) for other in joint.elements)
        candidates = (set(active_ids) - neighbor_ids - {element_id}) | set(self._excluded_elements)

        for other_id in sorted(candidates, key=str):
            try:
                other_bounds = self._bounds(other_id)
            except Exception:
                continue
            if not _bounds_overlap(swept, other_bounds):
                continue
            other = self.elements_by_id.get(other_id) or self._excluded_elements[other_id]
            try:
                other_box = other.obb
            except Exception:
                # No geometry to refine the broad-phase hit with, so keep the hit.
                return False
            if _swept_box_hits_box(box, direction, near, distance, other_box):
                return False
        return True

    def build(self):
        """Build the sequencing input.

        Returns
        -------
        :class:`~assembly_sequencing.boundary.SequencingInput`

        """
        element_ids = sorted(self.elements_by_id, key=lambda i: str(i))
        base_z = {}
        centroid_z = {}
        length = {}
        for element_id in element_ids:
            centerline = self.elements_by_id[element_id].centerline
            base_z[element_id] = min(centerline.start.z, centerline.end.z)
            centroid_z[element_id] = centerline.midpoint.z
            length[element_id] = centerline.length

        return SequencingInput(
            element_ids=element_ids,
            neighbors=self._neighbors(),
            joint_members=self._joint_members(),
            base_z=base_z,
            centroid_z=centroid_z,
            length=length,
            constraints=self.constraints,
            path_is_clear=self.path_is_clear if self.use_geometry else None,
            groups=self._groups(),
            excluded=self.excluded,
        )

    def manual_set_from_model(self):
        """Read the persisted hand-placement set off the element attributes.

        Returns
        -------
        set

        """
        manual = set()
        for element_id, element in self.elements_by_id.items():
            if element.attributes.get(MANUAL_ATTRIBUTE):
                manual.add(element_id)
        return manual

    def apply(self, result):
        """Write a sequence result back onto the model.

        Parameters
        ----------
        result : :class:`~assembly_sequencing.result.SequenceResult`

        """
        # Reaching into the private graph, in one place and on purpose: TimberModel has no
        # public setter for node attributes, and TimberModel.assembly_sequence reads the
        # sequence index straight off the graph node. A public API for this belongs
        # upstream in the model.
        graph = self.model._graph
        for index, element_id in enumerate(result.order):
            element = self.elements_by_id[element_id]
            vector = result.insertion_vectors[element_id]
            is_manual = element_id in result.manual_set
            state = result.extraction[element_id].state

            element.attributes[SEQUENCE_ATTRIBUTE] = index
            element.attributes[VECTOR_ATTRIBUTE] = vector
            element.attributes[MANUAL_ATTRIBUTE] = is_manual
            element.attributes[STATE_ATTRIBUTE] = state

            node = element.graphnode
            if node is not None:
                graph.node_attribute(node, SEQUENCE_ATTRIBUTE, value=index)
                graph.node_attribute(node, VECTOR_ATTRIBUTE, value=vector)
                graph.node_attribute(node, MANUAL_ATTRIBUTE, value=is_manual)


def sequencing_input_from_model(model, use_geometry=True):
    """Flatten a timber model into a sequencing input.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
    use_geometry : bool, optional

    Returns
    -------
    :class:`~assembly_sequencing.boundary.SequencingInput`

    """
    return TimberModelAdapter(model, use_geometry=use_geometry).build()


def generate_assembly_sequence(
    model,
    manual_set=None,
    pinned_order=None,
    strategy=None,
    width=None,
    distance=APPROACH_DISTANCE,
    use_geometry=True,
    apply_to_model=True,
):
    """Sequence a timber model and, by default, write the result onto it.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
    manual_set : iterable, optional
        Element ids (``str(element.guid)``) to treat as hand-placed. Defaults to whatever
        is already persisted on the elements, so that an amended set survives a re-run.
    pinned_order : dict or list, optional
        Element id -> assembly index, or a list of element ids in assembly order.
    strategy : :class:`~assembly_sequencing.preferences.PreferenceStrategy`, optional
    width : int, optional
        Beam width.
    distance : float, optional
        Approach distance for the swept broad-phase check, in model units.
    use_geometry : bool, optional
        Whether to run the swept broad-phase check at all.
    apply_to_model : bool, optional
        Write the sequence onto element and graph attributes.

    Returns
    -------
    tuple
        ``(result, adapter)``. The adapter carries the id -> element mapping needed to turn
        ids back into elements.

    """
    adapter = TimberModelAdapter(model, use_geometry=use_geometry)
    sequencing_input = adapter.build()

    if manual_set is None:
        manual_set = adapter.manual_set_from_model()

    kwargs = {"manual_set": manual_set, "pinned_order": pinned_order, "strategy": strategy, "distance": distance}
    if width is not None:
        kwargs["width"] = width

    result = generate_sequence(sequencing_input, **kwargs)

    if apply_to_model:
        adapter.apply(result)

    return result, adapter
