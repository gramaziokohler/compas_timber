"""Diagnose why an assembly sequence got stuck.

Run this from a terminal, not from Grasshopper -- Rhino does not show Python stdout, and
it caches imported modules for the life of the session, so edits to the package have no
effect until Rhino restarts. Export the model from Grasshopper first::

    # in a Grasshopper Python component
    model.to_json(r"C:\\path\\to\\model.json")

then::

    python scripts/debug_sequencing.py C:\\path\\to\\model.json

Answers, in order:

1. Which copy of the package is actually being imported.
2. Whether the swept collision check is what is blocking the sequence.
3. For the first stuck element: the constraints it carries, the directions the cone solver
   found, and -- for each of those -- exactly which other elements the swept check says are
   in the way.

"""

import sys

from compas.data import json_load

import assembly_sequencing
from assembly_sequencing import extract
from assembly_sequencing import rank_candidates
from assembly_sequencing.constraints import HalfSpace
from assembly_sequencing.constraints import SignedAxis
from assembly_sequencing.solver import APPROACH_DISTANCE
from compas_timber.planning.sequencing import TimberModelAdapter


def describe_environment():
    print("=" * 78)
    print("1. ENVIRONMENT")
    print("=" * 78)
    print("  python                 :", sys.executable)
    print("  assembly_sequencing    :", assembly_sequencing.__file__)
    print("  APPROACH_DISTANCE      :", APPROACH_DISTANCE, "model units")
    print()


def compare_with_and_without_geometry(model, distance=APPROACH_DISTANCE):
    from compas_timber.planning import generate_assembly_sequence

    print("=" * 78)
    print("2. IS THE SWEPT COLLISION CHECK THE PROBLEM?")
    print("=" * 78)
    print("  approach distance:", distance)
    with_geometry, _ = generate_assembly_sequence(model, distance=distance, apply_to_model=False)
    without, _ = generate_assembly_sequence(model, use_geometry=False, apply_to_model=False)

    for label, run in (("ON ", with_geometry), ("OFF", without)):
        total = len(run.order) + (len(run.stuck.remaining) if run.stuck else 0)
        print("  swept check %s : complete=%-5s  placed=%d of %d" % (label, run.is_complete, len(run.order), total))
    print()
    if without.is_complete and not with_geometry.is_complete:
        print("  >> The joint kinematics are fine. The swept broad-phase check is rejecting")
        print("     directions that are probably not really obstructed. See section 3.")
    elif not without.is_complete:
        print("  >> Still stuck without any collision checking, so this is the joint")
        print("     constraints themselves, not the geometry. Look at the constraints in")
        print("     section 3 and check the joints that produced them.")
    print()
    return with_geometry


def explain_first_stuck_element(model, result, distance=APPROACH_DISTANCE):
    if result.stuck is None:
        print("Not stuck - nothing to explain.")
        return

    adapter = TimberModelAdapter(model)
    data = adapter.build()

    active = set(result.stuck.remaining)
    element_id = result.stuck.remaining[0]
    element = adapter.elements_by_id[element_id]

    print("=" * 78)
    print("3. WHY IS THIS ELEMENT STUCK?")
    print("=" * 78)
    print("  element   :", element.name or element_id)
    print("  guid      :", element_id)
    print("  reason    :", result.stuck.blockers[element_id])
    print("  remaining : %d elements" % len(active))
    print()

    neighbors = data.active_neighbors(element_id, active)
    constraints = data.constraints(element_id, neighbors)
    print("  active jointed neighbours: %d" % len(neighbors))
    print("  constraints from them    : %d" % len(constraints))
    for constraint in constraints:
        print("     ", constraint)
    print()

    # What the cone solver alone thinks, with no collision checking at all.
    bare = extract(data, element_id, active, distance)
    print("  ignoring collisions, the solver says:", bare)
    print()

    normals = [c.normal for c in constraints if isinstance(c, HalfSpace)]
    axes = [c.direction for c in constraints if isinstance(c, SignedAxis)]
    directions = [(0.0, axis) for axis in axes] if axes else rank_candidates(normals)
    if not directions:
        # No constraints at all: the element is free, and the only direction the solver
        # ever proposes is straight up. If that is obstructed it is the sweep, full stop.
        from assembly_sequencing.solver import FREE_DIRECTION

        directions = [(1.0, FREE_DIRECTION)]

    print("  candidate directions, best margin first, and what obstructs each:")
    for margin, direction in directions[:6]:
        blockers = obstructions(adapter, element_id, direction, distance, active)
        label = "CLEAR" if not blockers else "blocked by %d" % len(blockers)
        print("     margin %+.4f  (%+.3f, %+.3f, %+.3f)  %s" % (margin, direction.x, direction.y, direction.z, label))
        for other_id in blockers[:5]:
            other = adapter.elements_by_id.get(other_id)
            print("         %s" % (other.name or other_id if other is not None else other_id))
        if len(blockers) > 5:
            print("         ... and %d more" % (len(blockers) - 5))
    print()
    print("  Note: this check is axis-aligned bounds around the swept oriented box. For a")
    print("  long beam running diagonally, that box is far larger than the beam, so a")
    print("  reported collision may well not be a real one.")


def obstructions(adapter, element_id, direction, distance, active_ids):
    """Which elements the swept broad-phase says are in the way. Empty means clear."""
    from compas_timber.planning.sequencing import _bounds_overlap
    from compas_timber.planning.sequencing import _element_id
    from compas_timber.planning.sequencing import _swept_aabb

    element = adapter.elements_by_id[element_id]
    swept = _swept_aabb(element.obb, direction, distance)
    neighbor_ids = set(_element_id(other) for joint in adapter._joints_for(element) for other in joint.elements)
    candidates = (set(active_ids) - neighbor_ids - {element_id}) | set(adapter._excluded_elements)

    hits = []
    for other_id in sorted(candidates, key=str):
        try:
            if _bounds_overlap(swept, adapter._bounds(other_id)):
                hits.append(other_id)
        except Exception:
            continue
    return hits


def main(path, distance=APPROACH_DISTANCE):
    describe_environment()
    model = json_load(path)
    model.process_joinery()
    result = compare_with_and_without_geometry(model, distance)
    explain_first_stuck_element(model, result, distance)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit("usage: python scripts/debug_sequencing.py <model.json> [approach_distance]")
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else APPROACH_DISTANCE)
