"""Score several ranking strategies against the same model.

There is no strategy that is best everywhere. Which one wins is a property of the model --
a stick frame, a reciprocal roof and a stacked log wall want different orders -- so the
honest way to choose is to run them and look at the numbers.

This module runs :func:`~assembly_sequencing.search.generate` once per strategy and reports
the handful of measurements that distinguish a good sequence from a merely valid one. It
deliberately does **not** collapse them into a single score: the weighting between "fewer
tight fits" and "less travel" is the user's call about their shop, not this package's.

Read the metrics like this:

===================  ========================================================================
``is_complete``      Did every element find a position? Nothing else matters until this does.
``tight``            Zero-clearance placements. Fewer is safer for a robot.
``mean_margin``      Average clearance angle in degrees. Bigger is more forgiving.
``min_margin``       The worst single placement. This is the one that will bite.
``hand_placed``      Elements exempted from the kinematic filter -- real fabrication work.
``cluster_switches`` Times the sequence jumps between subassemblies. Fewer is tidier.
``chain_continuity`` Fraction of placements that touch something already placed.
``height_inversions`` Times the sequence places something lower than what came before.
``support_inversions`` Jointed pairs where the higher one is placed before the lower one.
===================  ========================================================================

``height_inversions`` and ``support_inversions`` are not the same measurement and the
second is the one to read first. A height inversion counts every step that goes downhill,
including the harmless one where the sequence finishes a low bay and moves to a high one.
A support inversion counts only pairs that are actually jointed to each other, so each one
is a beam going into the model before something underneath it that it is joined to -- the
kind a fabricator notices. A sequence can score badly on the first and perfectly on the
second, and that sequence is fine.

A support inversion is not automatically a defect either. When every extraction that would
avoid one is kinematically blocked, some element has to come out from under something, and
the number says how often that happened rather than that the ranking misbehaved.

Examples
--------
>>> from assembly_sequencing import HalfSpace, SequencingInput
>>> from assembly_sequencing.compare import compare_strategies, describe_comparison
>>> from compas.geometry import Vector
>>> constraints = {
...     ("post", frozenset(["beam"])): [HalfSpace(Vector(0, 0, -1))],
...     ("beam", frozenset(["post"])): [HalfSpace(Vector(0, 0, 1))],
... }
>>> data = SequencingInput(
...     element_ids=["post", "beam"],
...     neighbors={"post": {"beam"}, "beam": {"post"}},
...     base_z={"post": 0.0, "beam": 1.0},
...     centroid_z={"post": 0.5, "beam": 1.0},
...     length={"post": 1.0, "beam": 2.0},
...     constraints=lambda i, active: constraints.get((i, frozenset(active)), []),
... )
>>> reports = compare_strategies(data, ["gravity", "clearance"])
>>> [report.name for report in reports]
['gravity', 'clearance']
>>> reports[0].order
['post', 'beam']

"""

from .boundary import sort_key
from .preferences import STRATEGIES
from .preferences import make_strategy
from .search import generate


class StrategyReport(object):
    """What one strategy did on one model.

    Parameters
    ----------
    name : str
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    result : :class:`~assembly_sequencing.result.SequenceResult`

    Attributes
    ----------
    name : str
    result : :class:`~assembly_sequencing.result.SequenceResult`
        The full result, for anything this summary leaves out.
    is_complete : bool
    placed : int
    total : int
    hand_placed : int
    tight : int
    mean_margin : float
        Mean clearance angle in degrees over the feasible placements, or 0.0 if there are
        none.
    min_margin : float
        The smallest clearance angle in degrees, or 0.0 if there are no feasible
        placements.
    cluster_switches : int
    chain_continuity : float
        On 0..1. The first placement has nothing to touch and is not counted.
    height_inversions : int
    support_inversions : int

    """

    def __init__(self, name, sequencing_input, result):
        self.name = name
        self.result = result

        self.total = len(sequencing_input.element_ids)
        self.placed = len(result.order)
        self.is_complete = result.is_complete
        self.hand_placed = len(result.manual_set)
        self.tight = len(result.tight_fits)

        angles = [result.extraction[i].angle_degrees for i in result.order if result.extraction[i].is_feasible]
        self.mean_margin = sum(angles) / float(len(angles)) if angles else 0.0
        self.min_margin = min(angles) if angles else 0.0

        self.cluster_switches = _cluster_switches(result)
        self.chain_continuity = _chain_continuity(sequencing_input, result)
        self.height_inversions = _height_inversions(sequencing_input, result)
        self.support_inversions = _support_inversions(sequencing_input, result)

    def __repr__(self):
        return "StrategyReport({!r}, complete={}, tight={})".format(self.name, self.is_complete, self.tight)

    @property
    def order(self):
        """list : The assembly order this strategy produced."""
        return list(self.result.order)

    def row(self):
        """This report as one line of the comparison table.

        Returns
        -------
        str

        """
        return "{:<14} {:<5} {:>7} {:>7} {:>9.1f} {:>9.1f} {:>7} {:>9} {:>8.2f} {:>10} {:>9}".format(
            self.name[:14],
            "yes" if self.is_complete else "NO",
            "{}/{}".format(self.placed, self.total),
            self.tight,
            self.mean_margin,
            self.min_margin,
            self.hand_placed,
            self.cluster_switches,
            self.chain_continuity,
            self.height_inversions,
            self.support_inversions,
        )


HEADER = "{:<14} {:<5} {:>7} {:>7} {:>9} {:>9} {:>7} {:>9} {:>8} {:>10} {:>9}".format(
    "strategy",
    "done",
    "placed",
    "tight",
    "mean deg",
    "min deg",
    "byhand",
    "switches",
    "chain",
    "inversions",
    "unsupp",
)
"""str: The column header matching :meth:`StrategyReport.row`."""


def _cluster_switches(result):
    switches = 0
    previous = None
    for index, element_id in enumerate(result.order):
        label = result.subassemblies.get(element_id)
        if index and label != previous:
            switches += 1
        previous = label
    return switches


def _chain_continuity(sequencing_input, result):
    if len(result.order) < 2:
        return 1.0
    placed = set()
    touching = 0
    for index, element_id in enumerate(result.order):
        if index and sequencing_input.neighbors[element_id] & placed:
            touching += 1
        placed.add(element_id)
    return float(touching) / float(len(result.order) - 1)


def _support_inversions(sequencing_input, result):
    """Jointed pairs the sequence puts the higher element into the model first.

    Counted over pairs rather than over steps: what matters is that a specific element went
    in before a specific lower element it is joined to, not where in the sequence that
    happened.

    """
    position = {element_id: index for index, element_id in enumerate(result.order)}
    inversions = 0
    for element_id in result.order:
        for higher_id in sequencing_input.above(element_id):
            if higher_id in position and position[higher_id] < position[element_id]:
                inversions += 1
    return inversions


def _height_inversions(sequencing_input, result):
    inversions = 0
    previous = None
    for element_id in result.order:
        height = sequencing_input.base_z[element_id]
        if previous is not None and height < previous:
            inversions += 1
        previous = height
    return inversions


def compare_strategies(sequencing_input, strategies=None, **kwargs):
    """Run several strategies on one model and measure each.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    strategies : iterable, optional
        Each item is either a name from
        :data:`~assembly_sequencing.preferences.STRATEGIES` or a
        :class:`~assembly_sequencing.preferences.PreferenceStrategy` instance. Defaults to
        every registered strategy, in name order.
    **kwargs : dict
        Passed straight to :func:`~assembly_sequencing.search.generate` -- `manual_set`,
        `pinned_order`, `width`, `distance`. The same values go to every strategy, which is
        the point: only the ranking differs.

    Returns
    -------
    list of :class:`StrategyReport`
        In the order the strategies were given.

    """
    if strategies is None:
        strategies = sorted(STRATEGIES)

    reports = []
    for item in strategies:
        strategy = make_strategy(item) if isinstance(item, str) else item
        result = generate(sequencing_input, strategy=strategy, **kwargs)
        reports.append(StrategyReport(strategy.name, sequencing_input, result))
    return reports


def describe_comparison(reports, show_orders=False):
    """Format a list of reports as a table.

    Parameters
    ----------
    reports : iterable of :class:`StrategyReport`
    show_orders : bool, optional
        Also print each strategy's assembly order, and how many positions it shares with
        the first report's order. Useful for spotting the strategies that are only
        nominally different on a given model.

    Returns
    -------
    str

    """
    reports = list(reports)
    lines = [HEADER, "-" * len(HEADER)]
    for report in reports:
        lines.append(report.row())

    if show_orders and reports:
        baseline = reports[0]
        lines.append("")
        lines.append("assembly orders (agreement is shared positions with {!r}):".format(baseline.name))
        for report in reports:
            shared = sum(1 for a, b in zip(baseline.order, report.order) if a == b)
            lines.append("  {:<14} {}/{} agree  {}".format(report.name, shared, len(baseline.order), [str(i) for i in report.order]))

    complete = [report.name for report in reports if report.is_complete]
    lines.append("")
    if not complete:
        lines.append("No strategy completed this model. Look at the stuck report before comparing anything else.")
    else:
        lines.append("Completed: {}.".format(", ".join(sorted(complete, key=sort_key))))
        lines.append("There is no single winner column -- pick the metric that matches the shop.")
    return "\n".join(lines)
