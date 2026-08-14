# Assembly Sequencing via Kinematic Escape Constraints

How `compas_timber` computes a robotic assembly order, a per-element insertion vector, and
an explicit set of elements that must be placed by hand.

Implemented in the top-level `assembly_sequencing` package, with the model adapter in
`compas_timber.planning.sequencing`.

---

## 1. Purpose and consumers

Forward-planning an assembly sequence runs into kinematic dead ends, so the algorithm works
backwards: **disassembly planning**. It repeatedly pulls an element clear of whatever is
still in place, then reverses the order and negates the vectors.

Three consumers, in priority order:

1. **Robotic assembly** — `compas_fab` consumes the unit insertion vector. The approach
   distance is fixed, short, and decided downstream.
2. **Visualization** — Grasshopper display of order and direction.
3. **Human fabrication** — the hand-placement set is a real fabrication instruction.

The tool must work acceptably on all designs and let the user override both the order and
the hand-placement set. Every design has exceptions; the job is to get close and make the
exceptions easy to express, not to be right unaided.

---

## 2. Where the code lives

```
src/
  compas_timber/                        the timber library
    planning/sequencing.py              TimberModel -> SequencingInput adapter
  assembly_sequencing/                  standalone, geometry-light
    boundary.py     SequencingInput — everything the algorithms may touch
    constraints.py  HalfSpace, SignedAxis, validation
    solver.py       pure: solve(constraints) -> Solution | Locked
    blocking.py     blocking graph, SCC, intrinsic locks, articulation points
    search.py       beam search over disassembly states, and generate()
    preferences.py  injectable ranking strategies; gravity is one of them
    result.py       SequenceResult, StuckReport, StalenessReport
```

`assembly_sequencing` imports nothing from `compas_timber`. In a single wheel this is
enforced structurally: the reverse dependency already exists, so any import back would be
circular.

Dependencies are `compas.geometry` and the standard library — no numpy, no scipy. Python
3.9 syntax, because it must run under Rhino's CPython.

**Constraint computation stays on the joint classes**, where the joint's private geometry
lives. Only consumption moved.

---

## 3. The joint interface

`Joint.get_kinematic_constraint(moving_element)` returns the freedom to pull
`moving_element` out, assuming every other member of that joint is frozen.

| Return | Meaning |
|---|---|
| `Vector` | Inward normal of a permitted half-space: `n · d >= 0`. Butt joints, laps. |
| `list[Vector]` | Several half-spaces; the freedom is their intersection. |
| `Line` | A strict 1-DOF sliding axis. Mortise-tenon, dovetail, housed seat cut. |

### 3.1 The `Line` is signed

This is the most surprising part of the protocol, and it was previously written down
nowhere.

A `Line` means **`start` → `end` is the only permitted extraction direction.** Its reverse
pushes deeper into the joint.

- The solver tests `direction` and never `-direction`. If the one permitted direction
  pushes through material, the element is locked.
- Two anti-parallel axes are a genuine deadlock, not a sign mistake. `abs()` in that test
  would be a bug.
- Two axes that are merely *near*-parallel are also a lock: two exact 1-DOF constraints
  with nothing to give really are over-constrained. The threshold is `PARALLEL_TOL`, about
  0.26°.
- The `Line`'s origin is carried through to `SignedAxis.origin` for callers that want to
  draw it. **The solver never reads it.**

Worked example — `TTenonMortiseJoint`: `main_beam` gets `+axis`, `cross_beam` gets `-axis`.

### 3.2 Unknown types raise

Anything that is not a `Line`, a `Vector`, or a list of those raises a `TypeError` in the
adapter. Dropping an unrecognised constraint makes an element look *more* free than it is,
which is the dangerous direction to fail in.

### 3.3 The permissive base implementation

The base `Joint.get_kinematic_constraint` falls back to a single half-space pointing from
the static element's centerline midpoint to the moving element's. That almost always yields
a valid extraction, and a large fraction of the joint library still relies on it.

Constraints from the fallback are tagged **inferred**, counted per element as
`Solution.inferred_count`, and totalled as `SequenceResult.inferred_total`. A result that
depended on guesses says so. Once joint coverage is good, unimplemented joints should
return a locked constraint instead — loud and honest.

---

## 4. The solver

Pure geometry: `solve(constraints, path_check=None) -> Solution | Locked`. No model, no
joint classes, no Rhino. That is what makes it testable against hand-built constraint sets.

### 4.1 Three extraction states

| State | Condition | Meaning |
|---|---|---|
| **Roomy** | `margin >= ROOMY_MARGIN` | Comfortable clearance, safe for robotic extraction |
| **Tight** | `-TOL <= margin < ROOMY_MARGIN` | A real but zero-clearance fit — a slot. Feasible, risky |
| **Locked** | `margin < -TOL` | No direction satisfies all constraints |

`margin` is `min_i (n_i · d)`, the sine of the angle by which the chosen direction clears
its nearest constraint boundary. **Margin classifies; it never rejects.** A beam dropped
into a slot between two others has a margin of exactly zero, and that is a correct answer
about a genuinely tight fit. Report `Solution.angle_degrees`: "3.2°" tells a fabricator
something, "tight" does not.

A strict 1-DOF fit is a slot by definition, so it is never roomy however generous the
surrounding half-spaces are.

`None` is not part of the vocabulary. An **empty** constraint list means the element is
entirely free, not locked.

### 4.2 Cone feasibility

```
maximise   min_i (n_i · d)
subject to |d| = 1
```

**Argmax over the candidate set, not first hit.** The candidates are the extreme rays of
the polyhedral cone: each `n_i`, both signs of each normalized pairwise cross `n_i × n_j`,
and the normalized sum of all normals as an interior seed. Crosses against world X/Y/Z are
not included; they are noise.

One degenerate case is handled explicitly. When two normals are anti-parallel their cross
vanishes and the feasible set collapses into the plane they share — a linear subspace with
no extreme rays. An orthonormal basis of that plane is added, so a beam housed between two
parallel faces is reported as the tight fit it is rather than as a lock.

Exact ties in margin are settled by alignment with the interior seed, then world up, then
rounded components. Output is therefore deterministic and independent of the order the
constraints arrived in.

### 4.3 Named constants

| Name | Value | Meaning |
|---|---|---|
| `ROOMY_MARGIN` | `sin(5°) ≈ 0.087` | Boundary between roomy and tight |
| `PARALLEL_TOL` | `1e-5` | 1-DOF parallelism, as `dot > 1 - PARALLEL_TOL` (~0.26°) |
| `TOL` | `1e-9` | Numeric zero |
| `APPROACH_DISTANCE` | `100.0` | Swept-check distance, model units |

### 4.4 Swept broad-phase

Constraints derived from joints only see *jointed* neighbours. In a dense lattice a beam
can be kinematically free per its joints while its extraction path passes straight through
a beam it is not jointed to — and the solver would report a clean vector with a comfortable
margin.

After the cone solve, `path_is_clear(element, d, APPROACH_DISTANCE, active_ids)` sweeps the
element against everything still in place. If the argmax direction fails, the next
candidate by descending margin is tried before declaring the element locked.

The adapter's implementation is axis-aligned bounds around the swept oriented box. It skips
jointed neighbours, whose interaction is already described exactly by the joint constraints
and which a beam sliding along a joint face would otherwise collide with by definition.
Excluded elements are treated as present. Being a broad phase, it errs towards "obstructed",
which is the safe direction for a robot.

---

## 5. Intrinsic vs. order-dependent locks

These are not the same failure and never share an output flag.

- **Intrinsic** — locked in every order. Detected up front and reported before sequencing
  starts. This is the only thing that legitimately produces a hand-placement flag.
- **Order-dependent** — locked given what is still in place, extractable under a different
  order. This is a failure of the sequence, and the search routes around it. It must never
  reach a shop floor as "place by hand".

### 5.1 The blocking graph

`A -> B` means "B must be removed before A, whatever the order". The edge test is
**pairwise**: an edge exists when the joint between A and B locks A *on its own*, with
everything else already gone. That makes it an unconditional precedence.

The tempting stronger rule — draw an edge to every neighbour that participates in locking A
in the complete assembly — is unsound. Blocking is disjunctive: an element freed by removing
*either* B *or* C would get edges to both, turning an OR into an AND and inventing cycles
where a good order exists.

Strongly connected components of size > 1 are mutually blocking clusters: **intrinsic
locks**. A rafter housed on both sides of a plate is the canonical case — cut the model down
to just those two and they are still stuck.

This is a reduced form of Wilson & Latombe's non-directional blocking graph (~1994). The
full sphere partition is not implemented; the SCC pass gives what is needed for a fraction
of the work, and is the road if subassembly-level sequencing is wanted later.

**Sound but not complete.** Every cluster reported really is locked in every order. An
interlock that only closes across three or more elements at once — each pair separable, the
trio not — has no pairwise edge to find and is not reported. Those surface as a
`StuckReport` from the search, which is the honest outcome: no order was *found*, rather
than a claim that none exists.

### 5.2 Subassemblies

User-declared model groups win. Otherwise the SCCs supply real, geometry-derived groups, and
an element in no cluster is its own subassembly. Labels derive from element ids, never
iteration order, so two runs on identical input give identical labels.

This replaces label propagation, which broke ties on `(count, guid)` — and since guids are
random, subassembly labels differed between runs on identical input, making the whole
ranking non-deterministic. Non-deterministic output on a fabrication tool is a correctness
defect.

### 5.3 N-ary joints

A member's constraint depends on which *other* members of its joint are still present, so
`SequencingInput.constraints` is a function of `(element_id, active_neighbor_ids)`, not a
per-joint lookup table. A two-element joint is the degenerate case. Ball-node and multibeam
joints contribute precedence like any other.

---

## 6. Search

**Beam search**, width 5 by default, over disassembly states, memoized on
`frozenset(remaining)`. Reversed at the end for assembly; vectors negated for insertion.

Chosen over memoized DFS because the goal is *a good* sequence, not merely *a* sequence.
Beam search is deterministic, degrades gracefully instead of falling off a node-budget
cliff, has no "best partial found" ambiguity, and makes alternative sequences nearly free.

Per step, per beam:

1. Filter the remaining elements to those with a `Solution`. Manual-set members always pass.
2. Rank the feasible set by the preference function.
3. Extend, keep the *k* best partials.

**Hard constraints filter; soft preferences rank.** They are separate mechanisms, so a
constraint violation cannot be outvoted by an ordering accident.

**Pins win.** A pin claims one assembly position and forbids every other. If a pinned
position is infeasible, a `PinConflict` is returned and sequencing stops. A user's
fabrication plan is never silently reordered.

**Dead ends** produce a `StuckReport`: step index, remaining elements, and the blocking
reason per element. A structured result, not a log line into a void that Grasshopper does
not display.

---

## 7. Ranking

The preference function is injectable; `GravityStrategy` is the default, not the only thing
the package can express. Its score, most significant term first:

1. **Does not strand anything from the ground.** One Tarjan articulation-point pass answers
   this for all candidates at once in O(V+E). What it measures is connectivity to a
   lowest-level element — a topological proxy, not a stability calculation.
2. **`base_z`, then `centroid_z`**, both descending, as two separate lexicographic terms.
   Both carry real signal: centroid alone ranks a ground-standing post as "high", base alone
   cannot separate two beams starting at the same level. *Summing* them produces a quantity
   with no physical meaning and no nameable unit.
3. **Roomy before tight.**
4. **Subassembly continuity.**
5. **Chain continuity**, then **length**, then **low connectivity**.

Element ids break exact ties, so the ranking never depends on dict iteration order.

**Beams only, for now, stated out loud.** Plates, panels, fasteners and group containers are
excluded from sequencing and listed in `SequenceResult.excluded`. Giving them a height of
zero sinks them to the bottom of the ranking while looking like a real measurement.

Deliberately absent: any rule ordering `cross_beam` before `main_beam`. "Main" and "cross"
are naming conventions about which beam got cut, not statements about assembly order, and
such a rule would override the geometry the solver computes.

---

## 8. Overrides

`generate(input, manual_set, pinned_order)` is idempotent and re-runnable.

1. The solver proposes a manual set: intrinsic locks, plus tight fits as candidates
   (`SequenceResult.proposed_manual_set`).
2. The user amends it.
3. Re-run with the amended set as a given.

Elements in the manual set are exempt from the feasibility filter — a human can rotate, tilt
and spring a member into place, so robot kinematics do not apply to them.

**Persistence.** The manual set is a fact about the design, so it lives in the element
attribute `requires_manual_assembly` and is serialized with the model; the adapter reads it
back on the next run. Pinned order is a fact about a particular build and is supplied per
run by the caller.

**Staleness.** When the model changes under an override — a pinned element deleted, a
position out of range, two pins on one position, an override on an excluded element — a
`StalenessReport` lists every override that no longer applies. A fabrication instruction
someone typed is never dropped without saying so.

---

## 9. Known limitations, accepted

- **Cone feasibility is infinitesimal freedom.** `min_i(n_i · d) > 0` says the element can
  *begin* to move, not that it can travel far enough to clear the assembly. The swept check
  mitigates this over the fixed approach distance; it does not eliminate the gap for deep
  mortises, scarfs, or long engagements.
- **No clearance distance.** Maximum travel before collision is expensive and the approach
  distance is fixed and short downstream. Deliberately not computed.
- **The robot is not a point.** Gripper and arm collision with already-placed elements is
  `compas_fab`'s domain. A sequence certified here can still be unbuildable for reach
  reasons, and users will experience that as this tool being wrong.
- **Monotone sequences only.** No assemble → disassemble → reassemble.
- **Intrinsic-lock detection is sound but not complete** (§5.1).
- **The swept check is a broad phase** (§4.4).

---

## 10. Usage

```python
from compas_timber.planning import generate_assembly_sequence

result, adapter = generate_assembly_sequence(model)

if not result.is_complete:
    print(result.stuck.describe())

for index, element_id in enumerate(result.order):
    beam = adapter.elements_by_id[element_id]
    vector = result.insertion_vectors[element_id]   # None => place by hand
    state = result.state(element_id)                # roomy | tight | locked
```

`generate_assembly_sequence` writes `assembly_sequence`, `insertion_vector`,
`requires_manual_assembly` and `extraction_state` onto the elements and the model graph.

`InsertionSolver` and `KinematicSequenceGenerator` remain exported from
`compas_timber.planning`, still running their original implementation. They are kept as a
fallback until the new path has been verified against real designs, and nothing in the new
path imports them — the two are independent and can be run on the same model and compared.
Retiring them is a separate decision; the small cleanups listed for
`kinematic_sequencer.py` are outstanding until then.

To sequence something that is not a timber model, build a
`assembly_sequencing.SequencingInput` directly and call
`assembly_sequencing.generate`; see `tests/assembly_sequencing/synthetic.py`.
