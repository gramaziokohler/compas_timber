# Candidates to upstream from `steko_branch`

Generic (non-Steko) changes found on `steko_branch`, beyond what's already been
extracted:

- `applied_features` tracking + `Dowel.drill_line` — already pushed to
  `refactor-fasteners` (commit `c8250fabf8`).
- `Pocket`/`Lap`/`BTLxPart` `BrepFace` API fixes (`compas_brep` migration) +
  `Pocket.apply()` negative `start_depth` guard — **now merged into `main`**
  (came in via PR from `fix-compas-brep-face-api`). `steko_branch` took
  `main`'s version of these three files wholesale when merging `main` in
  (2026-09), so nothing left to upstream here.
- The older "apply fastening features only to the elements referenced by the
  anchor" fixes to `dowel.py`/`fastener.py`/`ball_node.py` (commit
  `4261ab0ab7`) — superseded by `refactor-fasteners`' own
  "Split staged FastenerSystem from resolved `Fastener` element" rewrite
  (commit `75442736e4`); those three files are now byte-identical to
  `refactor-fasteners`.
- `elements/layer.py`'s line-wrapping/formatting divergence from `main` (seen
  when diffing `steko_branch` against `main`) is not a functional fix, just
  local formatting drift (multi-line-wrapped calls vs. `main`'s ruff-compact
  style) from an earlier commit. Needs a `ruff format` pass locally, not an
  upstream PR.

Two new bugs found and fixed while merging `refactor-fasteners` in (2026-09),
not yet reflected upstream:

- `fasteners/screw.py`, `Screw.compute_elementgeometry()`: `shank_brep +
  head_brep` returns a `list` under `compas_brep>=0.3.0` (the operator's
  boolean-union contract changed), not a single `Brep` — breaks any caller
  that treats the result as one Brep (e.g. `.is_valid`). This is literally
  what broke `test_screw_fastener.py` before the fix. Same class of bug as
  the already-known `PlateFastener`/`BallNodeFastener` `+=`/`-=` issue.
  Fix: `brep_union_first(shank_brep, head_brep)`.
- `fasteners/plate_fastener.py`, `RectangularPlate.compute_elementgeometry()`:
  same bug, `box_brep -= hole.geometry` → `box_brep =
  brep_difference_first(box_brep, hole.geometry)`.

Everything below is still sitting only on `steko_branch`, uncommitted-to-main.
Comparison baseline: `refactor-fasteners..steko_branch`.

## Safe to upstream as-is

Self-contained, no dependency on the Steko or fasteners-refactor work.

### `.gitignore`

Adds ignores for editor/tool artifacts: `.claude`, `.dev`, `.zed`, `*.ghx`,
`*.3dm`.

### `examples/model/0011_t_dovetail_joint.py` (new file)

Standalone example script demonstrating `TDovetailJoint` with a
`compas_viewer` viewer. Unrelated to fasteners/Steko.

### `src/compas_timber/elements/panel.py`

```python
def compute_modeltransformation(self):
    """A panel's transformation is always an absolute (world) placement, not relative to whatever
    element it happens to be nested under, so it must not be composed with ancestor transformations."""
    if self.model and self.model.transformation:
        return self.model.transformation * self.transformation
    return self.transformation
```

Fixes `Panel.compute_modeltransformation()`: unlike most elements, a panel's
own `transformation` is already an absolute/world placement rather than
parent-relative, so composing it with an ancestor's transformation (the
default `Element.compute_modeltransformation()` behavior) double-applies the
ancestor's transform. Already carries a docstring explaining why. Narrowly
scoped to `Panel`, low risk.

### `src/compas_timber/fabrication/slot.py`

```python
@inclination.setter
def inclination(self, inclination):
    inclination = abs(inclination)
    if inclination > 179.9 or inclination < 0.1:
        raise ValueError(...)
```

One-line fix: takes `abs(inclination)` before validating range, so a
legitimately-valid angle that computes out slightly negative (magnitude
still in range) doesn't spuriously fail the `0.1–179.9` check. Small,
targeted, low risk.

## Needs confirmation before upstreaming

### `src/compas_timber/base.py`

```python
# TimberElement.__data__
data["frame"] = self.frame                                     # old
data["frame"] = Frame.from_transformation(self.transformation)  # new
```

`self.frame` resolves to `Frame.from_transformation(self.modeltransformation)`
— the world-composed frame, baking in the whole ancestor chain.
`Frame.from_transformation(self.transformation)` serializes just the
element's own *local* transformation (relative to its parent).

This affects `__data__` for **every** `TimberElement` (`Beam`, `Plate`,
`Panel`, etc.), not just fasteners — high blast radius.

Working theory: this is a correctness fix for nested elements (a
`FastenerPart` under a `Fastener`, a `Layer` under a `Panel`). Serializing
the world-composed frame would bake in a snapshot of the ancestor's position
at serialize-time; reattaching the deserialized element to a parent would
then double-apply that ancestor's transform. For top-level (non-nested)
elements, `transformation` and `modeltransformation` should coincide, so the
change should be a no-op there — but this hasn't been verified with a
dedicated round-trip test for a *nested* element, and the original commit
(`a8ec2e9109`, message "steko?joint", 2026-08-07) has no explanatory context.

**Before upstreaming:** confirm the original motivating bug, and add/verify a
round-trip serialization test for a nested `TimberElement` (e.g. a
`FastenerPart` inside a `Fastener` inside a `TimberModel`) that would have
failed under the old behavior.

## Out of scope here

- The bulk of the `refactor-fasteners` branch itself (fasteners restructuring,
  docs, examples, tests) — a separate, already-tracked effort, not something
  introduced by the Steko work.
- Everything Steko-specific (`steko_joint.py`, `steko_fastener.py`, their
  `__init__.py` exports) — excluded per instruction.
