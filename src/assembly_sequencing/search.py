"""Beam search over disassembly states, and the package entry point.

Disassembly is searched rather than assembly because an element's freedom is decided by
what is still around it, which shrinks monotonically as disassembly proceeds. The result
is reversed at the end and the vectors negated to give assembly.

**Beam search, not memoized DFS.** The goal is *a good* sequence, not merely *a*
sequence. Beam search is deterministic, degrades gracefully rather than falling off a
node-budget cliff, has no "best partial found so far" ambiguity, and makes "show me three
alternative sequences" nearly free -- which the override workflow wants anyway.

"""

from .blocking import build_blocking_graph
from .blocking import disconnecting_elements
from .blocking import extract
from .blocking import ground_ids
from .blocking import intrinsic_locks
from .blocking import subassemblies as compute_subassemblies
from .boundary import sort_key
from .preferences import GravityStrategy
from .preferences import RankingContext
from .preferences import rank
from .result import TIGHT
from .result import PinConflict
from .result import SequenceResult
from .result import StalenessReport
from .result import StuckReport
from .solver import APPROACH_DISTANCE
from .trace import trace
from .trace import tracing

DEFAULT_BEAM_WIDTH = 5
"""int: How many partial disassembly sequences are carried forward per step."""


class _Partial(object):
    """One partial disassembly sequence carried by the beam."""

    __slots__ = ("remaining", "order", "solutions", "scores")

    def __init__(self, remaining, order, solutions, scores):
        self.remaining = remaining
        self.order = order
        self.solutions = solutions
        self.scores = scores

    def extended(self, element_id, solution, score):
        solutions = dict(self.solutions)
        solutions[element_id] = solution
        return _Partial(
            self.remaining - {element_id},
            self.order + (element_id,),
            solutions,
            self.scores + (score,),
        )


class _ExtractionCache(object):
    """Memoizes extraction results, which depend only on the element and the active set."""

    def __init__(self, sequencing_input, distance):
        self.input = sequencing_input
        self.distance = distance
        self._cache = {}

    def get(self, element_id, active_ids):
        key = (element_id, active_ids)
        if key not in self._cache:
            self._cache[key] = extract(self.input, element_id, active_ids, self.distance)
        return self._cache[key]


def beam_search(
    sequencing_input,
    manual_set=None,
    pins=None,
    strategy=None,
    subassemblies=None,
    width=DEFAULT_BEAM_WIDTH,
    distance=APPROACH_DISTANCE,
):
    """Search for a disassembly order.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    manual_set : set, optional
        Elements exempt from the feasibility filter. A human can rotate, tilt and spring
        a member into place, so robot kinematics do not apply to them.
    pins : dict, optional
        Maps **disassembly step index** -> element id that must be removed at that step.
        :func:`generate` converts the caller's assembly-order pins into this form.
    strategy : :class:`~assembly_sequencing.preferences.PreferenceStrategy`, optional
        Defaults to :class:`~assembly_sequencing.preferences.GravityStrategy`.
    subassemblies : dict, optional
        Element id -> label, for the continuity term in ranking.
    width : int, optional
    distance : float, optional

    Returns
    -------
    tuple
        ``(order, solutions, stuck, pin_conflict)`` where `order` is the disassembly
        order found -- possibly partial, if `stuck` or `pin_conflict` is set.

    """
    manual_set = set(manual_set or ())
    pins = dict(pins or {})
    strategy = strategy or GravityStrategy()
    subassemblies = subassemblies or {}
    width = max(1, int(width))

    all_ids = frozenset(sequencing_input.element_ids)
    total = len(all_ids)
    if total == 0:
        return [], {}, None, None

    # A pin claims one step and forbids every other, otherwise ranking could spend the
    # element early and the pin would fail later as "already placed".
    step_of_pinned = {element_id: step for step, element_id in pins.items()}

    cache = _ExtractionCache(sequencing_input, distance)
    beams = [_Partial(all_ids, (), {}, ())]

    for step in range(total):
        successors = {}
        stuck_report = None
        pin_conflict = None

        for partial in beams:
            active = partial.remaining
            last_removed = partial.order[-1] if partial.order else None

            grounded = ground_ids(sequencing_input, active)
            disconnecting = disconnecting_elements(sequencing_input, active, grounded)
            context = RankingContext(sequencing_input, active, last_removed, subassemblies, disconnecting, step)

            feasible = {}
            blockers = {}
            for element_id in sorted(active, key=sort_key):
                reserved_step = step_of_pinned.get(element_id)
                if reserved_step is not None and reserved_step != step:
                    blockers[element_id] = "pinned to assembly position {}".format(total - 1 - reserved_step)
                    continue
                result = cache.get(element_id, active)
                if result.is_feasible or element_id in manual_set:
                    feasible[element_id] = result
                else:
                    blockers[element_id] = result.reason

            pinned = pins.get(step)
            if pinned is not None:
                assembly_index = total - 1 - step
                if pinned not in active:
                    pin_conflict = pin_conflict or PinConflict(assembly_index, pinned, "element was already placed earlier in the sequence")
                    continue
                if pinned not in feasible:
                    pin_conflict = pin_conflict or PinConflict(
                        assembly_index,
                        pinned,
                        "cannot be extracted at this position: {}".format(blockers.get(pinned, "unknown")),
                    )
                    continue
                feasible = {pinned: feasible[pinned]}

            if not feasible:
                if stuck_report is None:
                    stuck_report = StuckReport(step, active, blockers)
                if tracing():
                    trace("step {}: DEAD END, all {} remaining elements are blocked".format(step, len(active)))
                    for blocked_id in sorted(active, key=sort_key):
                        trace("    {}: {}".format(blocked_id, blockers.get(blocked_id, "unknown")))
                continue

            for score, element_id in rank(context, feasible, strategy)[:width]:
                child = partial.extended(element_id, feasible[element_id], score)
                existing = successors.get(child.remaining)
                if existing is None or child.scores > existing.scores:
                    successors[child.remaining] = child

        if not successors:
            best = beams[0]
            trace("stopped at step {} of {} with {} placed".format(step, total, len(best.order)))
            return list(best.order), best.solutions, stuck_report, pin_conflict

        beams = sorted(successors.values(), key=lambda partial: (partial.scores, tuple(sort_key(i) for i in partial.order)), reverse=True)[:width]

        if tracing():
            leader = beams[0]
            chosen = leader.order[-1]
            result = leader.solutions[chosen]
            trace(
                "step {:>3}: {:>3} active, {} beam(s) -> removed {} [{}{}]".format(
                    step,
                    len(leader.remaining) + 1,
                    len(beams),
                    chosen,
                    result.state,
                    " by hand" if chosen in manual_set else "",
                )
            )

    best = beams[0]
    trace("complete: {} elements sequenced".format(len(best.order)))
    return list(best.order), best.solutions, None, None


def _normalize_pins(sequencing_input, pinned_order, staleness):
    """Turn caller-supplied pins into ``{disassembly_step: element_id}``.

    Accepts either a mapping of element id -> assembly index, or a sequence of element
    ids interpreted as assembly positions 0, 1, 2, ...

    """
    total = len(sequencing_input.element_ids)
    if not pinned_order:
        return {}

    if isinstance(pinned_order, dict):
        requested = list(pinned_order.items())
    else:
        pinned_list = list(pinned_order)
        requested = [(element_id, index) for index, element_id in enumerate(pinned_list)]
        if len(pinned_list) != total:
            staleness.add(
                "pin",
                None,
                "pinned order lists {} elements but the model has {}; positions beyond the list are free".format(len(pinned_list), total),
            )

    by_index = {}
    for element_id, assembly_index in sorted(requested, key=lambda item: (item[1], sort_key(item[0]))):
        if element_id not in sequencing_input:
            reason = "pinned element is not in the model"
            if element_id in sequencing_input.excluded:
                reason = "pinned element is excluded from sequencing ({})".format(sequencing_input.excluded[element_id])
            staleness.add("pin", element_id, reason)
            continue
        if not 0 <= assembly_index < total:
            staleness.add("pin", element_id, "pinned position {} is outside 0..{}".format(assembly_index, total - 1))
            continue
        if assembly_index in by_index:
            staleness.add(
                "pin",
                element_id,
                "position {} is already pinned to {!r}; this pin was dropped".format(assembly_index, by_index[assembly_index]),
            )
            continue
        by_index[assembly_index] = element_id

    return {total - 1 - assembly_index: element_id for assembly_index, element_id in by_index.items()}


def _normalize_manual(sequencing_input, manual_set, staleness):
    """Filter a caller-supplied manual set, reporting anything that no longer applies."""
    kept = set()
    for element_id in sorted(set(manual_set or ()), key=sort_key):
        if element_id in sequencing_input:
            kept.add(element_id)
        elif element_id in sequencing_input.excluded:
            staleness.add(
                "manual",
                element_id,
                "hand-placed element is excluded from sequencing ({})".format(sequencing_input.excluded[element_id]),
            )
        else:
            staleness.add("manual", element_id, "hand-placed element is no longer in the model")
    return kept


def generate(
    sequencing_input,
    manual_set=None,
    pinned_order=None,
    strategy=None,
    width=DEFAULT_BEAM_WIDTH,
    distance=APPROACH_DISTANCE,
):
    """Produce an assembly order, insertion vectors and a hand-placement set.

    Idempotent and re-runnable: hand placement is an input as well as an output. The
    solver proposes a manual set -- intrinsic locks, plus tight fits as candidates -- the
    user amends it, and the amended set is handed back in as a given.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    manual_set : iterable, optional
        Elements the user has declared hand-placed. Exempt from the feasibility filter.
        This is a fact about the design, so the caller should persist it with the model.
    pinned_order : dict or list, optional
        Either element id -> assembly index, or a list of element ids in assembly order.
        A fact about a particular build, so it is supplied per run rather than stored.
        Pins win: an unhonourable pin is reported, never silently reordered around.
    strategy : :class:`~assembly_sequencing.preferences.PreferenceStrategy`, optional
    width : int, optional
    distance : float, optional
        Approach distance for the swept broad-phase check.

    Returns
    -------
    :class:`~assembly_sequencing.result.SequenceResult`

    """
    staleness = StalenessReport()
    user_manual = _normalize_manual(sequencing_input, manual_set, staleness)
    pins = _normalize_pins(sequencing_input, pinned_order, staleness)

    trace(
        "sequencing {} elements ({} excluded), geometry check {}".format(
            len(sequencing_input.element_ids),
            len(sequencing_input.excluded),
            "on" if sequencing_input.has_geometry else "OFF",
        )
    )

    graph = build_blocking_graph(sequencing_input, distance=distance)
    clusters = intrinsic_locks(graph)
    labels = compute_subassemblies(sequencing_input, graph)

    intrinsic_members = set()
    for cluster in clusters:
        intrinsic_members |= set(cluster)

    effective_manual = user_manual | intrinsic_members

    if tracing():
        trace("  intrinsic locks: {}".format(len(clusters)))
        for cluster in clusters:
            trace("    {}".format(sorted(cluster, key=sort_key)))
        trace("  hand-placed: {} from the user, {} intrinsic".format(len(user_manual), len(intrinsic_members)))
        for kind, element_id, message in staleness:
            trace("  stale {} override on {}: {}".format(kind, element_id, message))

    order, solutions, stuck, pin_conflict = beam_search(
        sequencing_input,
        manual_set=effective_manual,
        pins=pins,
        strategy=strategy,
        subassemblies=labels,
        width=width,
        distance=distance,
    )

    assembly_order = list(reversed(order))
    tight = set(element_id for element_id, result in solutions.items() if result.state == TIGHT)

    return SequenceResult(
        order=assembly_order,
        extraction=solutions,
        manual_set=effective_manual,
        proposed_manual_set=intrinsic_members | tight,
        intrinsic_locks=clusters,
        subassemblies=labels,
        excluded=sequencing_input.excluded,
        staleness=staleness,
        stuck=stuck,
        pin_conflict=pin_conflict,
    )
