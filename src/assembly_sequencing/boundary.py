"""The boundary between a timber model and the sequencing algorithms.

:class:`SequencingInput` is the *complete* inventory of what the algorithms may touch.
Nothing in this package reaches past it, which is what makes the solver testable against
hand-written literals with no model, no Rhino and no joint classes.

Two members are callables rather than tables, deliberately:

* :meth:`SequencingInput.constraints` is a **function** of the element and the set of
  neighbours still in place. An n-ary joint's constraint on one member depends on which
  other members are still present, so a per-joint lookup table cannot express a ball
  node. A two-element joint is the degenerate case.
* :meth:`SequencingInput.path_is_clear` is a **callback**. The swept broad-phase check
  needs the geometry of every element and benefits from the host's spatial index.
  Keeping it behind a callback leaves geometry on the host side and keeps this package
  geometry-light.

"""

SUPPORT_TOLERANCE_FRACTION = 1e-3
"""float: The default support tolerance, as a fraction of the model's height.

How much higher a jointed neighbour's base must sit before
:meth:`SequencingInput.above` counts it as resting on the element, expressed against the
model rather than in any one unit -- this package is handed millimetres by one caller and
metres by another, and an absolute default would be either meaningless or catastrophic
depending on which arrived.

A thousandth of the model's height is deliberately generous towards "same level". The
quantity being compared is the lowest corner of an element's bounding box, and on a frame
of members at compound angles that corner lands a fraction of a millimetre apart on
members that are, for any purpose a fabricator has, at the same height. On the braced
canopy this was measured against, a thousandth came to 1 mm and separated 30 such pairs of
noise from 19 real ones with nothing in between.

"""


def sort_key(element_id):
    """Deterministic ordering key for element ids of any hashable type.

    Element ids are frequently guids, which are not mutually comparable and whose
    iteration order is not stable. Everything in this package that needs a tie-break
    sorts through this function so that two runs on identical input produce identical
    output.

    Parameters
    ----------
    element_id : hashable

    Returns
    -------
    str

    """
    return str(element_id)


class SequencingInput(object):
    """Everything the sequencing algorithms are allowed to know about a model.

    Parameters
    ----------
    element_ids : list
        All sequenceable element ids, in a stable order. Any hashable type.
    neighbors : dict
        Maps element id -> set of jointed neighbour ids. Must be symmetric.
    joint_members : dict, optional
        Maps joint id -> tuple of element ids. N-ary joints are represented as-is.
        Used for reporting; the algorithms read constraints through
        :meth:`constraints`.
    base_z : dict
        Maps element id -> the z of its lowest point.
    centroid_z : dict
        Maps element id -> the z of its centroid.
    length : dict
        Maps element id -> its length.
    constraints : callable
        ``f(element_id, active_neighbor_ids) -> list[Constraint]``.
    path_is_clear : callable, optional
        ``f(element_id, direction, distance, active_ids) -> bool``. Swept broad-phase
        against **all** active elements, not just jointed neighbours. Defaults to a
        function that always returns True, meaning "no geometry available"; the caller
        is then relying on joint constraints alone and can be fooled by a beam that is
        in the way but not jointed.
    groups : dict, optional
        Maps element id -> user-declared group label. Declared groups always win over
        inferred subassemblies.
    excluded : dict, optional
        Maps element id -> reason string, for elements deliberately left out of the
        sequence (plates, fasteners). These ids must not appear in `element_ids`; they
        are carried so the result can report them out loud rather than silently
        sequencing them at height zero.
    support_tolerance : float, optional
        How much higher a jointed neighbour's base must sit before :meth:`above` counts it
        as resting on this element, in model units. Defaults to
        :data:`SUPPORT_TOLERANCE_FRACTION` of the model's height. Raise it when members sit
        at compound angles and their bounding boxes disagree about a shared level; lower it
        on a model whose levels are genuinely finer than that.

    Raises
    ------
    ValueError
        If ids are duplicated, the neighbour map is asymmetric or incomplete, or any
        per-element quantity is missing. Missing quantities are an error rather than a
        default, because a silent ``0.0`` height sinks an element to the bottom of the
        ranking while looking like a real measurement.

    """

    def __init__(
        self,
        element_ids,
        neighbors,
        base_z,
        centroid_z,
        length,
        constraints,
        joint_members=None,
        path_is_clear=None,
        groups=None,
        excluded=None,
        support_tolerance=None,
    ):
        self.element_ids = list(element_ids)
        self._id_set = set(self.element_ids)
        if len(self._id_set) != len(self.element_ids):
            raise ValueError("element_ids contains duplicates.")

        self.neighbors = {key: set(value) for key, value in neighbors.items()}
        self.joint_members = dict(joint_members or {})
        self.base_z = dict(base_z)
        self.centroid_z = dict(centroid_z)
        self.length = dict(length)
        self.groups = dict(groups or {})
        self.excluded = dict(excluded or {})

        self._constraints_fn = constraints
        self._path_is_clear_fn = path_is_clear
        self._above = None

        self._validate()

        if support_tolerance is None:
            support_tolerance = self.height * SUPPORT_TOLERANCE_FRACTION
        self.support_tolerance = float(support_tolerance)
        if self.support_tolerance < 0.0:
            raise ValueError("support_tolerance must not be negative, got {!r}.".format(support_tolerance))

    def _validate(self):
        for element_id in self.element_ids:
            if element_id not in self.neighbors:
                raise ValueError("No neighbour entry for element {!r}.".format(element_id))
            for name, table in (("base_z", self.base_z), ("centroid_z", self.centroid_z), ("length", self.length)):
                if element_id not in table:
                    raise ValueError("No {} entry for element {!r}.".format(name, element_id))

        for element_id, neighbor_ids in self.neighbors.items():
            if element_id not in self._id_set:
                raise ValueError("Neighbour map mentions unknown element {!r}.".format(element_id))
            if element_id in neighbor_ids:
                raise ValueError("Element {!r} is listed as its own neighbour.".format(element_id))
            for neighbor_id in neighbor_ids:
                if neighbor_id not in self._id_set:
                    raise ValueError("Element {!r} has unknown neighbour {!r}.".format(element_id, neighbor_id))
                if element_id not in self.neighbors[neighbor_id]:
                    raise ValueError("Neighbour map is not symmetric: {!r} -> {!r}.".format(element_id, neighbor_id))

        for element_id in self.excluded:
            if element_id in self._id_set:
                raise ValueError("Element {!r} is both sequenceable and excluded.".format(element_id))

        if not callable(self._constraints_fn):
            raise ValueError("constraints must be callable.")
        if self._path_is_clear_fn is not None and not callable(self._path_is_clear_fn):
            raise ValueError("path_is_clear must be callable.")

    def __len__(self):
        return len(self.element_ids)

    def __contains__(self, element_id):
        return element_id in self._id_set

    def constraints(self, element_id, active_neighbor_ids):
        """Constraints on `element_id` given which of its neighbours are still in place.

        Parameters
        ----------
        element_id : hashable
        active_neighbor_ids : set
            The subset of :attr:`neighbors` ``[element_id]`` still present.

        Returns
        -------
        list of :class:`assembly_sequencing.constraints.Constraint`

        """
        return list(self._constraints_fn(element_id, set(active_neighbor_ids)))

    def path_is_clear(self, element_id, direction, distance, active_ids):
        """Whether `element_id` can sweep `distance` along `direction` without collision.

        Parameters
        ----------
        element_id : hashable
        direction : :class:`compas.geometry.Vector`
            Unit extraction direction.
        distance : float
            The fixed, short approach distance. This is not a question about maximum
            travel before collision, which this package deliberately does not answer.
        active_ids : set
            Every element still in place, jointed or not.

        Returns
        -------
        bool

        """
        if self._path_is_clear_fn is None:
            return True
        return bool(self._path_is_clear_fn(element_id, direction, distance, set(active_ids)))

    @property
    def has_geometry(self):
        """bool : True when a swept broad-phase callback was supplied."""
        return self._path_is_clear_fn is not None

    def active_neighbors(self, element_id, active_ids):
        """The neighbours of `element_id` that are still in place.

        Parameters
        ----------
        element_id : hashable
        active_ids : set

        Returns
        -------
        set

        """
        return set(self.neighbors[element_id]) & set(active_ids) - {element_id}

    @property
    def height(self):
        """float : How tall the model is, near enough to scale a tolerance by.

        Measured from the lowest base to the highest centroid, not across the bases alone.
        In a canopy or a tower every leg starts on the ground and the bases span almost
        nothing, while the structure itself is metres tall -- a tolerance derived from the
        bases there would be a small fraction of a small number and would not separate
        anything.

        """
        if not self.element_ids:
            return 0.0
        lowest = min(self.base_z[element_id] for element_id in self.element_ids)
        highest = max(max(self.base_z[element_id], self.centroid_z[element_id]) for element_id in self.element_ids)
        return highest - lowest

    def above(self, element_id):
        """The jointed neighbours whose base sits higher than this element's.

        Read it as "what is resting on this element", and read it sceptically: this is a
        height comparison over the joint graph, not a load path. Nothing in this package
        knows which element actually carries which. It is the same proxy :attr:`base_z`
        already supplies to the ranking, promoted from a sort key to a precedence -- of two
        jointed elements at different base heights, the higher one is taken to be resting
        on the lower, and so must be removed before it in disassembly and placed after it
        in assembly.

        Bases that agree to within :attr:`support_tolerance` put neither element above the
        other, which is what makes this a strict partial order: a cycle would need a chain
        of strictly increasing heights returning to its start, so there is always an order
        that honours every one of these precedences -- though not necessarily one that also
        satisfies the kinematics, which is why the ranking treats these as preferences and
        not as filters.

        The tolerance is not a rounding detail. Set it too fine and every jointed pair on a
        frame of angled members acquires a precedence from a fraction of a millimetre of
        bounding-box noise, the relation becomes very nearly a total order, and a term built
        on it can no longer tell anything apart.

        Parameters
        ----------
        element_id : hashable

        Returns
        -------
        set

        """
        if self._above is None:
            self._above = {
                key: set(neighbor_id for neighbor_id in neighbor_ids if self.base_z[neighbor_id] > self.base_z[key] + self.support_tolerance)
                for key, neighbor_ids in self.neighbors.items()
            }
        return self._above[element_id]

    def degree(self, element_id):
        """Number of jointed neighbours.

        Parameters
        ----------
        element_id : hashable

        Returns
        -------
        int

        """
        return len(self.neighbors[element_id])

    def sorted_ids(self, ids=None):
        """Element ids in deterministic order.

        Parameters
        ----------
        ids : iterable, optional
            Defaults to all sequenceable ids.

        Returns
        -------
        list

        """
        return sorted(self.element_ids if ids is None else ids, key=sort_key)
