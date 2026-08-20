# Fasteners

`compas_timber.fasteners` models the anatomy of what connects timber elements: dowels, screws, plates, and ball nodes.
A fastener is joint-agnostic — it does not know about `TButtJoint` or `BallNodeJoint` specifically. Instead, a joint
publishes a set of **anchors** (places on the joint's anatomy where something could attach), and a fastener declares
which kinds of anchor it accepts and how to place its own parts there.

## The anchor-based fastener system

* **`FastenerAnchor`** — a single attachment point published by a joint. It carries a `frame` (where and how it's
  oriented), a `kind` (see below), and the `elements` (beams) it references.
* **`AnchorKind`** — the small, stable vocabulary of geometric primitives an anchor can offer: `POINT` (0-D, e.g. a
  ball node), `AXIS` (1-D, e.g. a dowel or screw driven along a line), `FACE` (2-D, e.g. a plate), `VOLUME` (3-D).
* **`FastenerSystem`** — the *design-time recipe* for a fastener (e.g. `DowelFastenerSystem`, `ScrewFastenerSystem`).
  It declares `ACCEPTS` (the anchor kind(s) it consumes) and implements `bind(anchors)`, which builds and returns a
  brand-new `Fastener`. A system is plain data, not tied to any model — it can be authored once and bound to as many
  joints as needed; each `bind()` call produces its own independent fastener.
* **`Fastener`** — the *resolved*, model-ready container element that `bind()` returns, holding the `FastenerPart`
  children it staged.
* **`FastenerPart`** — the actual geometry-bearing piece (a `Dowel`, `Screw`, `RectangularPlate`, `BallNodeCore`, ...).
  A part's placement is expressed relative to its parent; parts can themselves own child parts (e.g. a ball node's
  core owns a rod per beam, and each rod owns a plate).

A typical usage pattern is therefore:

```python
system = SomeFastenerSystem(...)                                # 1. build the (joint-agnostic) fastener system
anchors = joint.fastener_anchors.of_kind(AnchorKind.SOME_KIND)  # 2. ask the joint for the anchors it accepts
fastener = system.bind(anchors)                                 # 3. bind: builds a fastener with parts at each anchor
model.add_fastener(fastener, joint.beams)                       # 4. add it to the model
model.process_joinery()
model.process_fasteners()                                       # 5. apply fabrication features to the beams
```

The sections below walk through each of the built-in fastener types. Every example starts from the same two beams
joined by a `TButtJoint` (except the ball node, which needs six beams meeting at a point). Runnable versions with a
live viewer are in `examples/fasteners/`.

## Dowel Fastener

A `DowelFastenerSystem` places one cylindrical `Dowel` at every `AXIS` anchor it is bound to, and drills a matching
hole into the connected beams.

```python
from compas.geometry import Line

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import DowelFastenerSystem
from compas_timber.fasteners.anchor import AnchorKind
from compas_timber.model import TimberModel

# Define the beams and connect them with a TButtJoint
cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [0.75, 0.5, 0.25]), width=0.05, height=0.05)
main_beam.frame.yaxis = [0, 0, 1]

model = TimberModel()
model.add_elements([cross_beam, main_beam])

joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True)

# WHAT: a joint-agnostic dowel fastener system
system = DowelFastenerSystem(diameter=0.02, length=0.1)

# WHERE: the joint publishes its attachment anchors; the system binds to the ones it accepts
anchors = joint.fastener_anchors.of_kind(AnchorKind.AXIS)
fastener = system.bind(anchors)

model.add_fastener(fastener, joint.beams)
model.process_joinery()
model.process_fasteners()

# Extract the geometries
beams = [beam.geometry for beam in model.beams]
dowels = fastener.geometry
```

See `examples/fasteners/example_dowel_fastener.py` for a runnable version with a live viewer.

## Plate Fastener

A `PlateFastenerSystem` places one `RectangularPlate` at every `FACE` anchor it is bound to. The plate can carry a
grid of holes and mill a recess into the beam it sits against.

```python
from compas.geometry import Line

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import PlateFastenerSystem
from compas_timber.fasteners.anchor import AnchorKind
from compas_timber.model import TimberModel

# Define the beams and connect them with a TButtJoint
cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [1, 1, 0]), width=0.05, height=0.05)

model = TimberModel()
model.add_elements([cross_beam, main_beam])

joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True, conical_tool=True)

# WHAT: a joint-agnostic plate fastener system
system = PlateFastenerSystem(width=0.04, height=0.05, thickness=0.005, recess=0.005, recess_offset=0.001)

# WHERE: the joint publishes its attachment anchors; the system binds to the ones it accepts
anchors = joint.fastener_anchors.of_kind(AnchorKind.FACE)
fastener = system.bind(anchors)

model.add_fastener(fastener, joint.beams)
model.process_joinery()
model.process_fasteners()

# Extract the geometries
beams = [beam.geometry for beam in model.beams]
plates = fastener.geometry
```

A plate can also carry a grid of holes, each optionally drilled through the beam:

```python
plate = fastener.parts[0]
plate.add_holes_grid(nx=5, ny=4, border_padding=0.005, diameter=0.004, drilling_depth=0.02, drilling_diameter=0.003)
```

See `examples/fasteners/example_plate_fasteners.py` for a runnable version (with a side-by-side visualization of the
model's hierarchy tree and interaction graph).

## Screw Fastener

`Screw` and `ScrewFastenerSystem` accept both `AXIS` and `POINT` anchors. A `ScrewFastenerSystem` bundles one or more
`Screw` parts into a reusable pattern: each screw's own `placement_frame` expresses its position *relative to the
anchor* it will be bound to (an offset within the group), defaulting to the anchor's frame itself when left unset.
Calling `bind()` builds a fastener staging a copy of every screw in the pattern at each accepted anchor.

A `Screw` can be built directly, or parsed from a standard designation string with `Screw.from_name` (e.g. `"8x120"`
or `"Ø8x120"`). It also carries a `precise` flag:

* `precise=False` (the default) — the geometry is just the cylindrical shank (`Cylinder`), cheap to compute.
* `precise=True` — the geometry is the shank unioned with a conical countersunk head into a single `Brep`. The head's
  size is controlled by `head_diameter` (default: twice the shank diameter) and `head_length` (default: the shank
  diameter).

```python
from compas.geometry import Frame
from compas.geometry import Line

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import Screw
from compas_timber.fasteners import ScrewFastenerSystem
from compas_timber.fasteners.anchor import AnchorKind
from compas_timber.model import TimberModel

# Define the beams and connect them with a TButtJoint
cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [0.75, 0.5, 0.25]), width=0.05, height=0.05)
main_beam.frame.yaxis = [0, 0, 1]

model = TimberModel()
model.add_elements([cross_beam, main_beam])

joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True)

# WHAT: a joint-agnostic screw fastener system; a pattern of two screws, offset side by side, comparing `precise`
screw_simple = Screw(diameter=0.008, length=0.12, placement_frame=Frame([-0.015, 0, 0], [1, 0, 0], [0, 1, 0]))
screw_precise = Screw(diameter=0.008, length=0.12, precise=True, placement_frame=Frame([0.015, 0, 0], [1, 0, 0], [0, 1, 0]))
system = ScrewFastenerSystem([screw_simple, screw_precise])

# WHERE: the joint publishes its attachment anchors; the system binds to the ones it accepts (AXIS or POINT)
anchors = joint.fastener_anchors.of_kind(AnchorKind.AXIS)
fastener = system.bind(anchors)

model.add_fastener(fastener, joint.beams)
model.process_joinery()
model.process_fasteners()

# Extract the geometries
beams = [beam.geometry for beam in model.beams]
screws = fastener.geometry
```

Each screw part also drills a pilot hole matching its diameter into the connected beams (see
`Screw.apply_fastening_features`), applied during `model.process_fasteners()`.

See `examples/fasteners/example_screw_fastener.py` for a runnable version.

## Ball Node Fastener

A `BallNodeFastenerSystem` binds to a single `POINT` anchor and builds a fastener with a nested hierarchy of parts
that mirrors the physical assembly: a central `BallNodeCore` owns one `BallNodeRod` per beam meeting at the node, and
each rod owns a `BallNodePlate` that bolts against the beam's end face. `BallNodeJoint` is what publishes that
`POINT` anchor, so it takes as many beams as meet at the node (not just two).

```python
from compas.geometry import Line

from compas_timber.connections import BallNodeJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import BallNodeFastenerParameters
from compas_timber.model import TimberModel

# Six beams radiating from the origin
length = 1.0
directions = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
beams = [Beam.from_centerline(Line([0, 0, 0], [d[0] * length, d[1] * length, d[2] * length]), width=0.05, height=0.05) for d in directions]

model = TimberModel()
model.add_elements(beams)

# The joint creates its ball-node fastener internally: it publishes a POINT anchor at the node and the
# (joint-agnostic) fastener binds to it, staging its core/rods/plates hierarchy. Parameters shape the fastener.
joint = BallNodeJoint.create(model, *beams, parameters=BallNodeFastenerParameters(ball_diameter=0.12, rods_length=0.15, plate_thickness=0.02, plate_depth=0.1))

model.process_joinery()
model.process_fasteners()

# Extract the geometries
beams_geo = [beam.geometry for beam in model.beams]
fastener_geo = []
for fastener in model.fasteners:
    fastener_geo.extend(fastener.geometry)
```

See `examples/fasteners/example_ball_node_fasteners.py` for a runnable version (with a side-by-side visualization of
the model's hierarchy tree and interaction graph).
