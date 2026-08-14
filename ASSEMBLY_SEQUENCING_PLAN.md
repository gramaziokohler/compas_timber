# Plan: `assembly_sequencing`

Implementation plan for extracting kinematic assembly sequencing out of
`compas_timber.planning` into a standalone package, and correcting its design.

Supersedes `KINEMATIC_PLANNING_REVIEW.md` (to be deleted in step 6) and drives a rewrite of
`KINEMATIC_CONSTRAINTS_SPEC.md`.

**Current state:** `src/compas_timber/planning/insertion_solver.py` and
`kinematic_sequencer.py`, both exported from `planning/__all__`, neither with any test
coverage.

---

## 1. Purpose

Produce an assembly order for a timber model, together with a per-element insertion vector
usable by `compas_fab` for trajectory planning, and an explicit set of elements that must be
placed by hand.

Three consumers, in priority order:

1. **Robotic assembly** — `compas_fab` consumes the unit insertion vector. Approach distance
   is fixed and short, decided downstream.
2. **Visualization** — Grasshopper display of order and direction.
3. **Human fabrication** — the hand-placement set is a real fabrication instruction.

The tool must work acceptably on all designs and let the user override both the order and the
hand-placement set. Every design has exceptions; the tool's job is to get close and make the
exceptions easy to express, not to be right unaided.

---

## 2. Architecture

### 2.1 Package layout

```
src/
  compas_timber/          existing
  assembly_sequencing/    new, top-level sibling
```

Same wheel, same repo, same version. Split into its own distribution later — record that
intent in the package `__init__` docstring so the second top-level package in the wheel is
not a mystery to the next reader.

**`assembly_sequencing` imports nothing from `compas_timber`.** In a single wheel this is
enforced structurally: the reverse dependency already exists, so any import back would be
circular. The boundary defends itself.

Dependencies: `compas.geometry` only. **No numpy, no scipy** — the solver is dot products and
cross products. Python 3.9 syntax (`Optional[X]`, not `X | None`); must run under Rhino's
CPython.

### 2.2 Module structure

```
assembly_sequencing/
  boundary.py     SequencingInput — everything the algorithms may touch
  constraints.py  Constraint types, validation
  solver.py       Pure. solve(constraints) -> Solution | Locked
  blocking.py     Blocking graph, SCC, intrinsic-lock detection
  search.py       Beam search over disassembly states
  preferences.py  Injectable ranking strategies; gravity is one of them
  result.py       SequenceResult, StuckReport, StalenessReport
```

`solver.py` is a pure geometric function testable against hand-built constraint sets with no
model, no Rhino, and no joint classes. That property is the point of the whole split.

### 2.3 The boundary

Complete inventory of what the algorithms need:

```python
class SequencingInput:
    element_ids            # ordered, stable
    neighbors              # id -> set of ids (jointed neighbors)
    joint_members          # joint_id -> tuple of ids (n-ary)
    base_z, centroid_z     # id -> float
    length                 # id -> float

    def constraints(self, element_id, active_neighbor_ids):
        """-> list[Constraint]. A FUNCTION, not a table."""

    def path_is_clear(self, element_id, direction, distance, active_ids):
        """-> bool. Swept broad-phase against ALL elements, not just neighbors."""
```

Two notes on shape:

- **`constraints` is a function.** An n-ary joint's constraint on a member depends on which
  other members are still present (§5.2). A per-joint lookup table cannot express a ball node.
- **`path_is_clear` is a callback.** The swept-OBB check (§4.4) needs the geometry of every
  element and benefits from `compas_timber`'s existing `rtree` index. Keeping it behind a
  callback leaves geometry on the timber side and keeps `assembly_sequencing` geometry-light.

`compas_timber` supplies a `TimberModel -> SequencingInput` adapter. Constraint *computation*
stays on the joint classes, where the joint's private geometry lives; only *consumption*
moves.

---

## 3. Feasibility semantics

The single most important correction. "No valid vector" currently means three unrelated
things, all collapsed into `None`.

### 3.1 Three extraction states

| State | Condition | Meaning |
|---|---|---|
| **Roomy** | `margin >= ROOMY_MARGIN` | Comfortable clearance, safe for robotic extraction |
| **Tight** | `-TOL <= margin < ROOMY_MARGIN` | Real but zero-clearance fit — a slot. Feasible, risky |
| **Locked** | `margin < -TOL` | No direction satisfies all constraints |

**Margin classifies; it never rejects.** A beam dropped vertically into a slot between two
others has a margin of exactly zero — the only feasible direction is exactly parallel to both
contact faces. That is a correct answer about a genuinely tight fit, not an artifact. Report
the angle as a number (`3.2°` tells a fabricator something; `tight` does not).

### 3.2 Intrinsic vs. order-dependent locks

These are not the same failure and must never share an output flag.

- **Intrinsic** — locked in the *complete* assembly, in every order. Double birdsmouth is the
  canonical case. Detected up front (§5.1) and reported before sequencing starts. This is the
  only thing that legitimately produces a hand-placement flag.
- **Order-dependent** — locked *given what is still in place*, extractable under a different
  order. This is a failure of the sequence. The search routes around it (§6). It must never be
  reported to a shop floor as "place by hand".

Today both produce `logging.warning` + `requires_manual_assembly = True`, so a mis-ordered
element is indistinguishable from one that physically needs hands.

### 3.3 Hand placement is an input as well as an output

`generate(input, manual_set, pinned_order)` — idempotent and re-runnable.

1. Solver proposes the manual set: intrinsic locks (§5.1), plus tight fits as *candidates*.
2. User amends it.
3. Re-run with the amended set as a given.

Elements in the manual set are exempt from the feasibility filter — a human can rotate, tilt,
and spring a member into place, so robot kinematics do not apply to them.

**Persistence:** the manual set is a fact about the design → persists in element attributes,
serialized with the model. Pinned order is a fact about a particular build → per-build,
supplied by the caller.

**Staleness:** when the model changes under an override — pinned element deleted, new elements
added — emit a `StalenessReport` listing every override that no longer applies. Never drop a
fabrication instruction the user typed without saying so.

---

## 4. Solver

Pure. No model reference.

### 4.1 Constraint types

- **Half-space** (`Vector` normal `n`): extraction direction `d` must satisfy `n · d >= 0`.
- **Signed axis** (`Line`): a strict 1-DOF direction, `start` → `end`. **Signed, not
  bidirectional** — this contract is currently written down nowhere and is the single most
  surprising part of the protocol. The existing code is correct here and the spec is wrong:
  - Testing only `base_dir`, never `-base_dir`, is correct. If the one permitted direction
    pushes through material, the element is locked.
  - Anti-parallel axes are a genuine deadlock. `abs()` here would be a bug.
  - The `Line`'s origin is carried but unused. Document that, or drop to `Vector` + a 1-DOF
    marker.
- **Unknown types raise.** They are currently dropped silently by the `if/elif` chain, and a
  dropped constraint makes an element look *more* free than it is — failure in the dangerous
  direction.

### 4.2 Cone feasibility

```
maximise   min_i (n_i · d)
subject to |d| = 1
```

**Argmax over candidates, not first hit.** The current code appends `Vector(0, 0, 1)` first
and returns the first passing candidate, so whenever straight-up is feasible at all it wins —
regardless of geometry, regardless of how marginal. Argmax makes output deterministic,
independent of candidate ordering, and yields the most interior direction.

Candidate set — the extreme rays of a 3D polyhedral cone:

- each `n_i`
- normalized pairwise crosses `n_i × n_j`, both signs
- the normalized sum of all `n_i` (interior seed)

Drop the axis-crosses against world X/Y/Z; they are noise.

### 4.3 Named constants, not literals

- `ROOMY_MARGIN` — `sin(5°) ≈ 0.087`. Boundary between roomy and tight.
- `PARALLEL_TOL` — for the 1-DOF parallelism test. `dot > 1 - 1e-5` is ~0.26°. The strictness
  is defensible (two exact 1-DOF constraints that are merely *near*-parallel really are
  over-constrained) but the reasoning must be attached to the name.
- `TOL` — numeric zero.

### 4.4 Swept broad-phase

Constraints derived from joints only see *jointed* neighbors. In a dense lattice a beam can be
kinematically free per its joints while its extraction path passes straight through a beam it
is not jointed to — and the solver will report a clean vector with a comfortable margin.

After the cone solve, call `path_is_clear(element, d, APPROACH_DISTANCE, active_ids)`: a swept
OBB against **all** remaining elements. This is cheap because the distance is fixed and short,
and it is a different question from "maximum travel before collision", which we are explicitly
not answering (§9).

If the argmax direction fails the sweep, try the next candidate by descending margin before
declaring locked.

### 4.5 Result types

```python
Solution(direction, margin, state, inferred_count)
Locked(reason)
```

`None` is retired. `resolve_constraints([])` currently returns `None` meaning *locked*, when
zero constraints means *entirely free* — the sequencer papers over this with a special-case
branch that disappears once the contract is honest.

`inferred_count` is the number of constraints that came from the permissive base
implementation (§10.1). A result that depended on guesses should say so.

---

## 5. Blocking graph

### 5.1 Intrinsic locks

Build a directed graph over the complete model: `A -> B` if `A` cannot be extracted while `B`
is present. Strongly connected components of size > 1 are mutually blocking clusters — locked
in every order. These are the intrinsic locks of §3.2, computed once rather than discovered by
brute force during search.

This is a reduced form of Wilson & Latombe's non-directional blocking graph (~1994). We are
not implementing the full sphere partition; the SCC pass over a single blocking relation gives
us what we need for a fraction of the work. If subassembly-level sequencing is wanted later,
the full NDBG is the road.

### 5.2 Subassemblies

SCCs also supply real subassemblies. This replaces label propagation, which broke ties on
`(count, guid)` — and since guids are random, **subassembly labels differed between runs on
identical input**, making the whole ranking non-deterministic. Non-deterministic output on a
fabrication tool is a correctness defect.

If the user has declared model groups, those win. Otherwise SCCs. Never an inferred grouping
dressed as intent.

### 5.3 N-ary joints

`_build_precedence_graph` currently skips any joint without exactly 2 elements, so ball-node
and multibeam joints — both with test coverage in this repo — contribute **zero** precedence
constraints. A ball node is precisely where sequencing is hard.

The general formulation: a member's constraint depends on which other members are still
present. A 2-element joint is the degenerate case. This is why `constraints` is a function of
`(element_id, active_neighbor_ids)`.

---

## 6. Search

**Beam search**, width k ≈ 5, over disassembly states. Reverse at the end for assembly; negate
vectors for insertion.

Chosen over memoized DFS because the goal is *a good* sequence, not merely *a* sequence. Beam
search is deterministic, degrades gracefully instead of falling off a node-budget cliff, has
no "best partial found" ambiguity, and makes "show me three alternative sequences" nearly free
— which the override workflow (§3.3) wants anyway.

Per step, per beam:

1. Filter remaining elements to those with a `Solution` (manual-set members always pass).
2. Rank the feasible set by the preference function (§7).
3. Extend, keep the k best partials, memoize on `frozenset(remaining)`.

**Hard constraints filter; soft preferences rank.** The current ten-tuple blends five booleans
and five continuous values into one lexicographic comparator, so a constraint violation can
only ever be outvoted by ordering accident. Separating them is what makes the behaviour
explainable, tunable, and testable.

**Pins win.** If a pinned position is infeasible, report the conflict and stop. Never silently
reorder a user's fabrication plan.

**Dead ends** produce a `StuckReport` — step index, remaining elements, and the blocking
constraint per element. A structured result, not a log line into a void that Grasshopper does
not even display.

---

## 7. Ranking

Injectable preference function. Bottom-up gravity becomes *one* strategy the package offers,
not the only thing it can express — the package is meant to hold several sequencing
algorithms.

Default gravity strategy:

- height as lexicographic `(base_z, centroid_z)`. Both terms carry real signal — centroid
  alone ranks a ground-standing post as "high"; base alone cannot separate two beams starting
  at the same level. But *summing* them (`min(start.z, end.z) + midpoint.z`, as today)
  produces a quantity with no physical meaning and no nameable unit, used simultaneously as a
  hard gate and a continuous sort key.
- roomy before tight — free, strictly better.
- subassembly continuity (§5.2).
- chain continuity, length, connectivity as tiebreaks.

**Deleted outright:**

- `_build_hierarchy_graph` — forces `cross_beam` before `main_beam` at a priority above every
  geometric signal. "Main" and "cross" are naming conventions about which beam got cut, not
  statements about assembly order, and the rule *overrides* the geometry the solver computes.
  Delete it and re-run the known-good model: if the order holds, it was redundant; if it
  breaks, a real constraint is missing from the solver and *that* is the bug.
- Label propagation (§5.2).
- The ten-tuple.

**Non-beam elements** (plates, fasteners) are excluded from sequencing with an explicit report.
Today they silently receive height `0.0` and sink to the bottom of the ranking — still
sequenced, just wrongly. Beams only, for now, stated out loud.

**`_creates_floating_component`** runs a full BFS per candidate per step — O(n³·E). One Tarjan
articulation-point pass answers it for all candidates at once, O(V+E), and shares machinery
with §5.1. Also: what it measures is *connectivity to a level-0 element*, a topological proxy
rather than a stability criterion. Name that honestly in the docstring.

---

## 8. Testing

Neither file has any test today, which means every claim in this plan is currently
unfalsifiable — there is no way to tell whether the argmax change improves output or merely
changes it.

1. **Synthetic fixture, first.** Hand-written adjacency map and hand-written constraint sets,
   ~20 lines of literals. No Rhino, no joint classes, no geometry engine. Include a birdsmouth
   case from day one so §3.2 has a test immediately. This is where a failure can be attributed
   to a cause.
2. **Real model, as regression net.** The Grasshopper design with a known-good order,
   serialized to JSON under `tests/`. Assert the full order; document each known exception
   explicitly. When this one fails it will not tell you *why* — a hundred interacting decisions
   produced that order — which is exactly why the synthetic fixture comes first.
3. **Sign regression on `mortise_tenon`.** The class previously defined
   `get_kinematic_constraint` twice with opposite signs. The surviving contract is `main_beam`
   → `+ axis`, `cross_beam` → `- axis`. That class of defect only ever surfaces as a sign flip
   in output, so pin it.

---

## 9. Known limitations, accepted

- **Cone feasibility is infinitesimal freedom.** `min_i(n_i · d) > 0` says the element can
  *begin* to move, not that it can travel far enough to clear the assembly. The swept-OBB
  check (§4.4) mitigates over the fixed approach distance; it does not eliminate the gap for
  deep mortises, scarfs, or long engagements.
- **No clearance distance.** Maximum travel before collision is expensive and the approach
  distance is fixed and short downstream. Deliberately not computed.
- **The robot is not a point.** Gripper and arm collision with already-placed elements is
  `compas_fab`'s domain. A sequence certified here can still be unbuildable for reach reasons,
  and users will experience that as this tool being wrong. Say so in the docs.
- **Monotone sequences only.** No assemble → disassemble → reassemble.

---

## 10. Loose ends in `compas_timber`

### 10.1 The permissive base implementation

`Joint.get_kinematic_constraint` (`connections/joint.py:253-276`) falls back to
`Vector.from_start_end(static.centerline.midpoint, moving.centerline.midpoint)` — a single
half-space pointing roughly beam-to-beam, which almost always yields a valid extraction. 16
files override it; there are 33 joint classes.

So a large fraction of the joint library currently reports near-total freedom by default, and
nothing distinguishes "computed" from "nobody implemented this joint". For a vector feeding
`compas_fab`, that is the failure direction that hurts.

**Now:** tag inferred constraints and surface `inferred_count` in results (§4.5). Some of the
"exceptions" in the known-good model may turn out to be missing implementations rather than
genuine design quirks.

**Later:** once coverage is good, unimplemented joints should return locked — loud and honest.

### 10.2 Small fixes

- Stray `print(len(cps))` at `t_birdsmouth.py:158`, in library code, in the joint named as the
  canonical hand-placed case.
- `t_birdsmouth.get_kinematic_constraint` docstring says "Does not yet work with the mill
  depth" while the code branches on `self.mill_depth`.
- Four docstrings promise a `Plane` return that no implementation produces —
  `joint.py:265`, `butt_joint.py:201`, `l_butt.py:152`, `l_lap.py:98`. The **code is right and
  the docstrings are wrong**; they return `list[Vector]`. Documentation fix only.
- `import logging` inside the loop body; magic `999` topological fallback leaking into a sort
  key; unused `remaining_elements` parameter; private reach-through to `model._graph`.

---

## 11. Work breakdown

Split first, fix in the new home. Every change on this list is behavioural and there are no
tests — making ten unverifiable changes to code that is about to move, then moving it, then
discovering which move broke what, is the expensive order. The boundary work is not extra
cost; it is what makes the fixture possible.

| # | Step | Acceptance |
|---|---|---|
| 1 | Package skeleton, `SequencingInput`, constraint types, synthetic fixture | Fixture builds with no `compas_timber` import; constraint validation raises on unknown types |
| 2 | Solver: argmax, margin classification, result types, swept-OBB hook | Same direction for a given constraint set regardless of candidate order; slot case classifies as tight, not locked; zero-constraint case returns free, not locked |
| 3 | Blocking graph, SCC → intrinsic locks and subassemblies | Birdsmouth fixture reports intrinsic lock before sequencing; two runs on identical input give identical labels |
| 4 | Beam search, `SequenceResult` / `StuckReport`, n-ary joints | Ball-node fixture produces precedence; dead-end produces a structured report, not a warning |
| 5 | Preference functions, override round-trip, staleness reporting | `generate` idempotent; pin conflict reported not silently resolved; deleted pinned element produces staleness report |
| 6 | `TimberModel` adapter, spec rewrite, §10 cleanups | Real GH model sequences end-to-end; `KINEMATIC_PLANNING_REVIEW.md` deleted; signed-`Line` contract documented in the spec |

---

## 12. Deferred by decision

- **Adapter location and the fate of `compas_timber.planning` exports.** `InsertionSolver` and
  `KinematicSequenceGenerator` stay in `planning/__all__` for now; `sequencer.py` is outdated
  and headed for deletion, but `BuildingPlan` / `Step` may survive in some form. How this
  integrates with the antikythera orchestrator is an open question, deliberately not answered
  here.
- **Full NDBG** — sphere partition and per-cell blocking graphs. The road if subassembly-level
  sequencing is wanted.
- **Standalone distribution** for `assembly_sequencing`.
