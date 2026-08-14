"""Injectable ranking strategies.

Hard constraints filter; soft preferences rank. The feasibility filter in
:mod:`assembly_sequencing.search` decides *whether* an element may be removed at a step;
a strategy here decides only *which of the permitted ones* is preferred. Blending the two
into one comparator, as a single lexicographic tuple of booleans and continuous values,
means a constraint violation can be outvoted by an ordering accident.

Bottom-up gravity is the default strategy, not the only expressible one -- this package is
meant to hold several sequencing algorithms.

"""

from .boundary import sort_key
from .result import ROOMY


class RankingContext(object):
    """The state a strategy may score against.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set
        Elements still in place, before this step's removal.
    last_removed : hashable or None
        The element removed at the previous step.
    subassemblies : dict
        Element id -> subassembly label.
    disconnecting : set
        Elements whose removal would strand part of the assembly from the ground, from
        :func:`~assembly_sequencing.blocking.disconnecting_elements`.
    step_index : int

    """

    def __init__(self, sequencing_input, active_ids, last_removed, subassemblies, disconnecting, step_index):
        self.input = sequencing_input
        self.active_ids = active_ids
        self.last_removed = last_removed
        self.subassemblies = subassemblies
        self.disconnecting = disconnecting
        self.step_index = step_index


class PreferenceStrategy(object):
    """Base class for ranking strategies."""

    name = "preference"

    def score(self, context, element_id, solution):
        """Score a candidate removal. Higher is better.

        Parameters
        ----------
        context : :class:`RankingContext`
        element_id : hashable
        solution : :class:`~assembly_sequencing.result.Solution` or :class:`~assembly_sequencing.result.Locked`
            The extraction result for this candidate in this state. Hand-placed elements
            may carry a ``Locked``.

        Returns
        -------
        tuple
            A comparable tuple. All candidates at a step must return tuples of the same
            shape.

        """
        raise NotImplementedError


class GravityStrategy(PreferenceStrategy):
    """Bottom-up assembly, which is top-down disassembly.

    The score, most significant term first:

    1. **Does not strand anything from the ground.** A topological proxy for stability,
       not a stability calculation, and the one term whose violation produces obvious
       nonsense -- so it leads.
    2. **base_z, then centroid_z**, both descending, as two separate lexicographic terms.
       Both carry real signal: centroid alone ranks a ground-standing post as "high",
       base alone cannot separate two beams that start at the same level. Summing them,
       as an earlier implementation did, produces a quantity with no physical meaning and
       no nameable unit -- and was then used simultaneously as a hard gate and a
       continuous sort key.
    3. **Roomy before tight.** Free clearance is strictly better than a zero-clearance
       slot, so spend the roomy extractions while there is still room.
    4. **Subassembly continuity** -- finish a cluster before starting another.
    5. **Chain continuity** -- prefer a neighbour of the last element removed.
    6. **Length**, then **low connectivity**, as tiebreaks. Long members and peripheral
       members come off first.

    """

    name = "gravity"

    def score(self, context, element_id, solution):
        sequencing_input = context.input

        stable = element_id not in context.disconnecting
        roomy = solution.state == ROOMY

        same_subassembly = False
        in_chain = False
        if context.last_removed is not None:
            same_subassembly = context.subassemblies.get(element_id) == context.subassemblies.get(context.last_removed)
            in_chain = context.last_removed in sequencing_input.neighbors[element_id]

        return (
            int(stable),
            sequencing_input.base_z[element_id],
            sequencing_input.centroid_z[element_id],
            int(roomy),
            int(same_subassembly),
            int(in_chain),
            sequencing_input.length[element_id],
            -sequencing_input.degree(element_id),
        )


class HeuristicStrategy(PreferenceStrategy):
    """Rank by a caller-supplied scalar function of the element id.

    An escape hatch for callers that want to express one idea -- "tallest first",
    "longest first" -- without subclassing.

    Parameters
    ----------
    function : callable
        ``f(element_id) -> float``. Higher scores are removed earlier.
    name : str, optional

    """

    def __init__(self, function, name="heuristic"):
        self.function = function
        self.name = name

    def score(self, context, element_id, solution):
        return (float(self.function(element_id)),)


def rank(context, candidates, strategy):
    """Order candidate removals, best first.

    Parameters
    ----------
    context : :class:`RankingContext`
    candidates : dict
        Element id -> extraction result.
    strategy : :class:`PreferenceStrategy`

    Returns
    -------
    list of tuple
        ``(score, element_id)`` pairs, best first. The element id is appended to the sort
        key so that equal scores resolve the same way on every run.

    """
    scored = [(strategy.score(context, element_id, result), element_id) for element_id, result in candidates.items()]
    scored.sort(key=lambda item: (item[0], sort_key(item[1])), reverse=True)
    return scored
