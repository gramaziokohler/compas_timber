"""Result types.

``None`` is retired from this package's vocabulary. It previously meant three unrelated
things at once -- "locked", "unconstrained" and "not computed" -- and the caller could
not tell them apart.

"""

import math

from .boundary import sort_key

ROOMY = "roomy"
"""str: Comfortable clearance around the extraction direction. Safe for robotic extraction."""

TIGHT = "tight"
"""str: A real but zero-clearance fit -- a slot. Feasible, and risky."""

LOCKED = "locked"
"""str: No direction satisfies all constraints."""


class Solution(object):
    """A feasible extraction.

    Parameters
    ----------
    direction : :class:`compas.geometry.Vector`
        Unit extraction direction. Negate for insertion.
    margin : float
        The sine of the smallest angle between `direction` and any constraint boundary.
        A margin of exactly zero is a correct answer about a genuinely tight fit, not a
        numerical artifact: a beam dropped into a slot between two others has exactly one
        feasible direction, parallel to both contact faces.
    state : str
        One of :data:`ROOMY` or :data:`TIGHT`.
    inferred_count : int
        How many of the constraints behind this result came from a permissive generic
        fallback rather than a joint-specific implementation.

    """

    def __init__(self, direction, margin, state, inferred_count=0):
        self.direction = direction
        self.margin = float(margin)
        self.state = state
        self.inferred_count = int(inferred_count)

    @property
    def is_feasible(self):
        """bool : Always True. Present so callers need not type-test."""
        return True

    @property
    def angle_degrees(self):
        """float : The clearance margin as an angle in degrees.

        Report this to fabricators. "3.2 degrees" tells someone something; "tight" does not.

        """
        return math.degrees(math.asin(max(-1.0, min(1.0, self.margin))))

    def __repr__(self):
        return "Solution({:.4f}, {:.4f}, {:.4f}, margin={:.4f}, {})".format(self.direction.x, self.direction.y, self.direction.z, self.margin, self.state)


class Locked(object):
    """No feasible extraction.

    Whether this is an *intrinsic* lock or an *order-dependent* one is not decided here
    -- it depends on the active set this result was computed against. See
    :mod:`assembly_sequencing.blocking`.

    Parameters
    ----------
    reason : str
        Human-readable explanation, carried through to :class:`StuckReport`.
    inferred_count : int, optional

    """

    def __init__(self, reason, inferred_count=0):
        self.reason = reason
        self.inferred_count = int(inferred_count)

    @property
    def is_feasible(self):
        """bool : Always False."""
        return False

    @property
    def state(self):
        """str : Always :data:`LOCKED`."""
        return LOCKED

    @property
    def direction(self):
        """None : A locked element has no extraction direction."""
        return None

    @property
    def margin(self):
        """float : Not a measurement; locked results carry no usable margin."""
        return float("nan")

    def __repr__(self):
        return "Locked({!r})".format(self.reason)


class StuckReport(object):
    """A dead end during search: a structured result, not a log line into a void.

    Parameters
    ----------
    step_index : int
        The disassembly step at which no element could be removed.
    remaining : iterable
        The element ids still in place.
    blockers : dict
        Maps element id -> the reason it could not be extracted at this step.

    """

    def __init__(self, step_index, remaining, blockers):
        self.step_index = int(step_index)
        self.remaining = sorted(remaining, key=sort_key)
        self.blockers = dict(blockers)

    def __repr__(self):
        return "StuckReport(step={}, remaining={})".format(self.step_index, len(self.remaining))

    def describe(self):
        """A multi-line human-readable summary.

        Returns
        -------
        str

        """
        lines = ["Stuck at disassembly step {} with {} elements remaining:".format(self.step_index, len(self.remaining))]
        for element_id in self.remaining:
            lines.append("  {}: {}".format(element_id, self.blockers.get(element_id, "unknown")))
        return "\n".join(lines)


class PinConflict(object):
    """A pinned position that cannot be honoured.

    Pins win: rather than silently reordering a plan someone typed, sequencing stops and
    reports this.

    Parameters
    ----------
    assembly_index : int
    element_id : hashable
    reason : str

    """

    def __init__(self, assembly_index, element_id, reason):
        self.assembly_index = int(assembly_index)
        self.element_id = element_id
        self.reason = reason

    def __repr__(self):
        return "PinConflict(index={}, element={!r}, {!r})".format(self.assembly_index, self.element_id, self.reason)


class StalenessReport(object):
    """Overrides that no longer apply to the model as it now stands.

    A fabrication instruction someone typed is never dropped without saying so.

    """

    def __init__(self, entries=None):
        self.entries = list(entries or [])

    def add(self, kind, element_id, message):
        """Record a stale override.

        Parameters
        ----------
        kind : str
            ``"manual"`` or ``"pin"``.
        element_id : hashable
        message : str

        """
        self.entries.append((kind, element_id, message))

    @property
    def is_empty(self):
        """bool"""
        return not self.entries

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __repr__(self):
        return "StalenessReport({} entries)".format(len(self.entries))

    def describe(self):
        """A multi-line human-readable summary.

        Returns
        -------
        str

        """
        if self.is_empty:
            return "No stale overrides."
        lines = ["{} override(s) no longer apply:".format(len(self.entries))]
        for kind, element_id, message in self.entries:
            lines.append("  [{}] {}: {}".format(kind, element_id, message))
        return "\n".join(lines)


class SequenceResult(object):
    """The output of :func:`assembly_sequencing.generate`.

    Parameters
    ----------
    order : list
        Element ids in **assembly** order.
    extraction : dict
        Maps element id -> :class:`Solution` or :class:`Locked`, as computed at the step
        that element was removed during the disassembly search.
    manual_set : set
        The elements that were exempt from the feasibility filter on this run -- the
        user's own set plus any intrinsic locks.
    proposed_manual_set : set
        What the solver suggests the manual set should be: intrinsic locks, plus tight
        fits as candidates. Feed it back in after amending it.
    intrinsic_locks : list of frozenset
        Mutually blocking clusters, locked in every order. The only thing here that
        legitimately means "place by hand".
    subassemblies : dict
        Maps element id -> subassembly label.
    excluded : dict
        Maps element id -> reason for exclusion from sequencing.
    staleness : :class:`StalenessReport`
    stuck : :class:`StuckReport`, optional
        Present only if the search dead-ended.
    pin_conflict : :class:`PinConflict`, optional
        Present only if a pin could not be honoured.

    """

    def __init__(
        self,
        order,
        extraction,
        manual_set,
        proposed_manual_set,
        intrinsic_locks,
        subassemblies,
        excluded=None,
        staleness=None,
        stuck=None,
        pin_conflict=None,
    ):
        self.order = list(order)
        self.extraction = dict(extraction)
        self.manual_set = set(manual_set)
        self.proposed_manual_set = set(proposed_manual_set)
        self.intrinsic_locks = [frozenset(cluster) for cluster in intrinsic_locks]
        self.subassemblies = dict(subassemblies)
        self.excluded = dict(excluded or {})
        self.staleness = staleness if staleness is not None else StalenessReport()
        self.stuck = stuck
        self.pin_conflict = pin_conflict

    @property
    def is_complete(self):
        """bool : True when every sequenceable element found a position."""
        return self.stuck is None and self.pin_conflict is None

    @property
    def insertion_vectors(self):
        """dict : Element id -> unit insertion vector, or None for hand-placed elements.

        The insertion vector is the negated extraction vector. `compas_fab` consumes it;
        the approach distance is decided downstream.

        """
        vectors = {}
        for element_id, result in self.extraction.items():
            direction = result.direction
            vectors[element_id] = None if direction is None else -direction
        return vectors

    def state(self, element_id):
        """The extraction state of an element.

        Parameters
        ----------
        element_id : hashable

        Returns
        -------
        str
            One of :data:`ROOMY`, :data:`TIGHT`, :data:`LOCKED`.

        """
        return self.extraction[element_id].state

    @property
    def tight_fits(self):
        """set : Elements whose extraction is feasible but has zero clearance."""
        return set(key for key, value in self.extraction.items() if value.state == TIGHT)

    @property
    def inferred_total(self):
        """int : Total number of constraints in this result that came from a fallback."""
        return sum(value.inferred_count for value in self.extraction.values())

    def __len__(self):
        return len(self.order)

    def __repr__(self):
        return "SequenceResult({} elements, complete={})".format(len(self.order), self.is_complete)

    def describe(self):
        """A multi-line human-readable summary.

        Returns
        -------
        str

        """
        lines = []
        for index, element_id in enumerate(self.order):
            result = self.extraction[element_id]
            flag = " [by hand]" if element_id in self.manual_set else ""
            if result.direction is None:
                lines.append("{:>3}. {} -- locked: {}{}".format(index, element_id, result.reason, flag))
            else:
                vector = -result.direction
                lines.append(
                    "{:>3}. {} -- insert ({:.3f}, {:.3f}, {:.3f}) {} {:.1f} deg{}".format(
                        index, element_id, vector.x, vector.y, vector.z, result.state, result.angle_degrees, flag
                    )
                )
        for element_id, reason in sorted(self.excluded.items(), key=lambda item: sort_key(item[0])):
            lines.append("  excluded: {} ({})".format(element_id, reason))
        if self.pin_conflict is not None:
            lines.append(repr(self.pin_conflict))
        if self.stuck is not None:
            lines.append(self.stuck.describe())
        if not self.staleness.is_empty:
            lines.append(self.staleness.describe())
        return "\n".join(lines)
