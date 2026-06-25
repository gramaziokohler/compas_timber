# compas_timber — Agent Context

## What this project is

`compas_timber` is a Python library for the parametric design and digital fabrication of timber frame structures. It models timber assemblies semantically — not as raw geometry, but as typed elements with relationships — and produces machine-readable BTLx fabrication files as its terminal output.

## The core invariant

**The model is parametric.** Elements (beams, joints) hold design intent as parameters. All geometry and fabrication features are derived from those parameters on demand. Nothing computed should be stored as ground truth in place of the parameters that produced it.

A change that bakes derived geometry back into the model — even if it produces visually correct output — violates the fundamental purpose of the library. This is the highest-priority thing to preserve. When in doubt, escalate to the human rather than make an assumption.

## Domain glossary

| Term | Definition | Do not confuse with |
|---|---|---|
| **TimberModel** | Top-level container for all elements and joints. Elements are graph nodes; joints are graph edges (via `compas_model`). | A plain scene graph or geometry container |
| **Beam** | A timber element with a rectangular cross-section. Its local frame defines: x = centerline/fibre direction, y = width, z = height. The stable, well-defined core element. | Generic mesh or geometry object |
| **Panel** | A planar timber element (e.g. CLT). Definition and implementation are actively contested — tread carefully. | Beam |
| **Plate** | A flat element type, also actively contested. Changes here leak across the library. | Panel |
| **Fastener** | A connector element (screws, dowels, etc.). Actively contested; changes leak. | A fabrication feature |
| **Shape** | The design geometry of a beam — what it looks like in the model. | Blank |
| **Blank** | The raw stock material geometry, including any extensions added for machining. Features are applied relative to the blank, not the shape. | Shape |
| **Feature** | A machining operation (cut, lap, tenon, mortise, drilling, etc.) applied to a beam's blank. Features drive BTLx output. Not metadata or annotations — they are the fabrication instructions. | A geometric attribute or property |
| **Joint** | A resolved, typed connection between two (or more) elements, with features applied to each. Created via `Joint.create()` on the appropriate subclass. | JointCandidate |
| **JointCandidate** | A detected geometric possibility — two elements are close enough to potentially connect. Not yet typed or feature-applied. | Joint |
| **Cluster** | Aggregates multiple JointCandidates for joints involving more than two beams. How a Cluster translates to a concrete Joint is an open design question — do not invent a resolution here. | Joint, JointCandidate |
| **JointTopology** | The topological classification of a connection: `L`, `T`, `X`, `Y`, `I`, `K` for beams; `EDGE_EDGE`, `EDGE_FACE` for plates. Detected by the solver before a joint type is assigned. | The joint type (e.g. LButtJoint) |
| **ref_sides** | The six numbered faces of a beam according to the BTLx standard. Features are anchored to a specific ref_side. Getting the wrong ref_side produces a cut on the wrong face of the physical timber. | Arbitrary face indices |
| **BTLx** | The machine-readable XML exchange format for CNC timber processing machines. The terminal output of the whole pipeline. Spec: https://www.design2machine.com/btlx/index.html | An internal data format |

## Architecture

```
compas_timber/
├── elements/        # Beam, Panel, Plate, Fastener — element definitions
├── connections/     # Joint subclasses, JointCandidate, Cluster, solver, topology detection
├── fabrication/     # BTLx feature classes (JackRafterCut, Lap, Tenon, Mortise, etc.)
├── btlx/            # BTLx serialization/reader
├── model.py         # TimberModel — top-level container
├── planning/        # Higher-level planning utilities
├── panel_features/  # Panel-specific features (contested area)
├── ghpython/        # LEGACY — do not touch
└── rhino/           # LEGACY — do not touch
```

**GH components** have been migrated to a separate repository. Do not modify `ghpython/` or `rhino/`.

**Layer boundary:** Core logic lives in `elements/`, `connections/`, `fabrication/`, and `model.py`. The BTLx layer is downstream — it consumes features, it does not define joint behavior.

**`compas_model` boundary:** `TimberModel` inherits from `compas_model.Model`; `Beam` inherits from `compas_model.elements.Element`. The rule: timber-specific logic belongs in `compas_timber`. Generic model mechanics that are not timber-specific are candidates to upstream to `compas_model`. Do not duplicate what `compas_model` already provides.

## Areas of active instability

`Beam` has a stable, long-standing definition. The following are **actively contested** — their definitions and implementations are subject to revision, and changes in them tend to leak across the library:

- `Plate`
- `Panel`
- `Fastener`
- Panel features (`panel_features/`)

When touching these, explicitly flag potential cross-library leakage before making structural changes.

## Adding a new joint type

Follow the contribution guide at `docs/contribution/joints_contribution_guide.md`. The pattern: subclass `Joint`, implement `add_features()` to apply fabrication operations to each connected element, and register the topology. Use an existing clean implementation as reference.

## Adding a new BTLx feature

Follow the contribution guide at `docs/contribution/BTLx_contribution_guide.md`.

If a feature anchors to a beam face, consult the BTLx ref_sides convention and the spec at https://www.design2machine.com/btlx/index.html.

## Pre-submission checklist

Run these before submitting any change:

1. `invoke format`
2. `invoke lint`
3. `invoke test`
4. If the change touches any joint or fabrication feature: verify BTLx params in a test using `params.as_dict()` comparison against a known-good fixture.
5. If the change adds or modifies any serializable type: add a **round-trip serialization test** (`__data__` → `__from_data__` → compare). This is a common pitfall.
6. If the change touches `Plate`, `Panel`, `Fastener`, or panel features: explicitly describe potential cross-library leakage in the PR description.

## Dev environment setup

```bash
uv venv
source .venv/bin/activate # on mac. on windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
invoke test      # run tests
invoke lint      # lint
invoke format    # format
invoke docs      # build docs
```

Tests use MM units by default (enforced by the session-scoped tolerance fixture in `conftest.py`). Do not hardcode tolerance values in tests — use `TOL` from `compas.tolerance`.

Brep-dependent tests currently cannot run on CI (due to the Brep host wrapper). This is expected to change. BTLx param comparison tests are the current gold standard for fabrication correctness on CI.

## Open design questions — escalate, do not resolve

- How a `Cluster` translates to a concrete multi-beam `Joint`
- Definition and boundaries of `Plate`, `Panel`, and `Fastener` element types
- Serialization backwards-compatibility strategy

If your change requires resolving one of these questions, stop and ask the human.
