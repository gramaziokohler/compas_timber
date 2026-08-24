"""Run every ranking strategy against one model and print the scores side by side.

Which strategy produces the best sequence is a property of the model, not of the package,
so the only honest way to choose one is to run them all and look. Export the model from
Grasshopper first::

    # in a Grasshopper Python component
    model.to_json(r"C:\\path\\to\\model.json")

then::

    python scripts/compare_strategies.py C:\\path\\to\\model.json

or name the ones you care about::

    python scripts/compare_strategies.py C:\\path\\to\\model.json gravity skeleton subassembly

Run this from a terminal, not from Grasshopper -- Rhino does not show Python stdout, and it
caches imported modules for the life of the session.

Reading the table
-----------------
``done`` first: a strategy that does not finish the model has no other score worth
comparing. After that there is no single winner column, because the trade is a fact about
the shop:

* A robot cell cares about ``tight`` and ``min deg`` -- a zero-clearance placement is the
  one that will jam.
* A crew on site cares about ``switches`` and ``chain`` -- how much walking the order
  implies.
* Anyone prefabricating cares about ``switches`` -- a sequence that finishes one panel
  before starting the next can be cut into panels.
* ``byhand`` is real fabrication work and is worth minimizing on any account.

The ``random`` row is a control, not a candidate. It is an arbitrary order that still
respects stability, and it is there to show what the other rows are worth: a strategy that
scores no better than ``random`` on your model is not earning its place there.

To tune your own, edit :func:`custom_strategies` below.

"""

import sys

from compas.data import json_load

from assembly_sequencing import STRATEGIES
from assembly_sequencing import WeightedStrategy
from assembly_sequencing import compare_strategies
from assembly_sequencing import describe_comparison
from assembly_sequencing import make_strategy
from compas_timber.planning.sequencing import TimberModelAdapter


def custom_strategies():
    """Hand-tuned strategies to compare alongside the registered ones.

    Weights are applied to terms normalized onto 0..1 over the model, so they are
    comparable across models and mean what they say. Give ``stable`` a weight big enough
    that nothing outvotes it unless you mean to let it.

    Returns
    -------
    list of :class:`~assembly_sequencing.preferences.PreferenceStrategy`

    """
    return [
        WeightedStrategy({"stable": 100.0, "base_z": 10.0, "roomy": 4.0, "subassembly": 2.0}, name="tuned-gravity"),
        WeightedStrategy({"stable": 100.0, "subassembly": 10.0, "locality": 6.0, "base_z": 3.0}, name="tuned-panels"),
    ]


def names_for(adapter, element_ids):
    """Element names where the model has them, ids where it does not."""
    labels = []
    for element_id in element_ids:
        element = adapter.elements_by_id.get(element_id)
        labels.append(str(element.name or element_id) if element is not None else str(element_id))
    return labels


def main(path, wanted=None):
    model = json_load(path)
    adapter = TimberModelAdapter(model)
    sequencing_input = adapter.build()

    strategies = [make_strategy(name) for name in (wanted or sorted(STRATEGIES))]
    if not wanted:
        strategies += custom_strategies()

    print("model               :", path)
    print("elements sequenced  :", len(sequencing_input.element_ids))
    print("elements excluded   :", len(sequencing_input.excluded))
    print("swept collision test:", "on" if sequencing_input.has_geometry else "OFF")
    print()

    reports = compare_strategies(sequencing_input, strategies)
    print(describe_comparison(reports))
    print()

    print("=" * 78)
    print("ASSEMBLY ORDERS")
    print("=" * 78)
    for report in reports:
        print("  {} ({})".format(report.name, "complete" if report.is_complete else "INCOMPLETE"))
        print("    " + ", ".join(names_for(adapter, report.order)))
        print()

    stuck = [report for report in reports if report.result.stuck is not None]
    if stuck:
        print("=" * 78)
        print("WHY THE UNFINISHED ONES STOPPED")
        print("=" * 78)
        print("  Every strategy hit the same wall? Then this is the constraints, not the")
        print("  ranking -- run scripts/debug_sequencing.py instead.")
        print()
        for report in stuck:
            print("  {}: {}".format(report.name, report.result.stuck.describe().splitlines()[0]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit("usage: python scripts/compare_strategies.py <model.json> [strategy ...]")
    main(sys.argv[1], sys.argv[2:] or None)
