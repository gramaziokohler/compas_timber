"""CompositeBeam example.

This script demonstrates a ``CompositeBeam``: an element that behaves like an ordinary
``Beam`` towards the rest of the model, while also being a container for its own parts.
Here the composite is an L-bracket made of two perpendicular ``Beam`` parts - a
deliberately non-linear arrangement, to show that a composite's parts don't need to sit
on a single axis.

The workflow is:
1. Build a ``CompositeBeam`` standalone, and add two perpendicular ``Beam`` parts to it
   directly (``add_part``) - this happens entirely outside the model.
2. Add the composite beam to the model, then call ``merge_contained_elements`` to
   add its parts as the composite's children in the model tree.
3. Add an internal lap joint (``LLapJoint``) directly between the two parts - an
   ordinary joint, with no composite-specific machinery involved.
4. Add an external beam and connect it to the *composite* with an ordinary
   ``ButtJoint`` - exactly as if the composite were a plain ``Beam``.
5. Call ``model.process_joinery()``. Before any joint computes anything,
   ``TimberModel`` calls ``Joint.resolve_composite_elements()`` on every joint,
   which swaps the composite for whichever of its parts the joint's (generic,
   joint-type-agnostic) ``location`` falls in - so the butt joint's cut lands on
   that real part, and never on the composite's own nominal envelope. No joint
   subclass needs to know ``CompositeBeam`` exists.

The end beam is deliberately positioned ~800mm short of part_a's end, so the trim is
large enough to actually see: watch for the gap between the ghosted grey composite
envelope (never cut) and the blue part_a geometry underneath it (visibly shorter).

Run this script from the repository root::

    python examples/model/0012_composite_beam.py

"""

import os

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import ButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.elements import Beam
from compas_timber.elements import CompositeBeam
from compas_timber.model import TimberModel

HERE = os.path.dirname(__file__)

WIDTH = 100
HEIGHT = 200

# ----- colours used in the viewer -----
COLOR_COMPOSITE = Color.grey()  # ghosted - the composite's own nominal envelope
COLOR_PART_A = Color.from_hex("#2B7CB8")  # blue  - straight part
COLOR_PART_B = Color.from_hex("#1DB847")  # green - perpendicular part
COLOR_END_BEAM = Color.from_hex("#E05C1A")  # orange - the beam that trims the composite


def build_model():
    # ------------------------------------------------------------------
    # 1. Build the composite beam and its two perpendicular parts, standalone.
    #    Their real positions define an L-bracket; the composite's own nominal
    #    envelope only needs to be a reasonable placeholder for external
    #    connections - it never has to match the parts' real shape.
    # ------------------------------------------------------------------
    composite_frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    composite = CompositeBeam(composite_frame, length=2000, width=WIDTH, height=HEIGHT)

    part_a = Beam(composite_frame, length=2000, width=WIDTH, height=HEIGHT)
    part_b = Beam(Frame(Point(2000, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), length=1000, width=WIDTH, height=HEIGHT)
    part_a.name = "part_a"
    part_b.name = "part_b"
    composite.add_part(part_a)
    composite.add_part(part_b)

    # An independent beam that meets part_a ~800mm short of its end - a large,
    # clearly visible trim, positioned well inside part_a's range (0-2000) and
    # far from the corner at (2000, 0, 0) so the routing is unambiguous.
    end_beam = Beam(Frame(Point(1200, -600, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=WIDTH, height=HEIGHT, length=1200)
    end_beam.name = "end_beam"

    # ------------------------------------------------------------------
    # 2. Add to the model. The composite's parts only become real tree
    #    children of the composite once merge_contained_elements is called.
    # ------------------------------------------------------------------
    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)
    model.add_element(end_beam)

    # ------------------------------------------------------------------
    # 3. Internal joint between the composite's own parts - an ordinary
    #    joint, unaware that its two elements happen to belong to a
    #    CompositeBeam.
    # ------------------------------------------------------------------
    LLapJoint.create(model, part_a, part_b)

    # ------------------------------------------------------------------
    # 4. External joint targeting the composite directly, exactly as if
    #    it were a plain Beam. mill_depth>0 also gives end_beam a visible
    #    Lap notch, so the joint produces two clearly visible cuts.
    # ------------------------------------------------------------------
    ButtJoint.create(model, composite, end_beam, mill_depth=20)

    # ------------------------------------------------------------------
    # 5. Resolve joinery. The butt joint's cut is routed to whichever
    #    part of the composite it actually intersects.
    # ------------------------------------------------------------------
    model.process_joinery()

    return model, composite, part_a, part_b, end_beam


def main():
    model, composite, part_a, part_b, end_beam = build_model()

    print(f"Elements in model : {len(list(model.elements()))}")
    print(f"Composite parts   : {[p.name for p in composite.parts]}")
    print(f"Composite features: {len(composite.features)} (0 expected - it stays a pure nominal envelope)")
    print(f"Composite envelope: {composite.centerline.start} .. {composite.centerline.end}")
    for part in composite.parts:
        print(f"  {part.name}: {len(part.features)} feature(s) ({[type(f).__name__ for f in part.features]}), centerline: {part.centerline.start} .. {part.centerline.end}")
    print(f"end_beam: {len(end_beam.features)} feature(s) ({[type(f).__name__ for f in end_beam.features]})")

    # ------------------------------------------------------------------
    # Visualise
    # ------------------------------------------------------------------
    viewer = Viewer()
    # The composite's own bounding region sits in the +X/+Y quadrant, not around the
    # world origin - point the camera at it explicitly, and scale distance/far-plane
    # to this ~2m model (the other examples' defaults are tuned for much bigger scenes).
    viewer.renderer.camera.target = [1000.0, 500.0, 0.0]
    viewer.renderer.camera.position = [-2000.0, -3000.0, 2500.0]
    viewer.renderer.camera.far = 100_000.0
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"

    # Ghost the composite's own nominal envelope for context. Its centerline
    # coincides with part_a's, so lift its tag above part_a's to avoid overlap.
    viewer.scene.add(composite.geometry, color=COLOR_COMPOSITE, opacity=0.15)
    composite_tag_position = composite.centerline.midpoint + Vector(0, 0, 300)
    viewer.scene.add(Tag(text="composite (no features)", position=composite_tag_position, height=25, color=COLOR_COMPOSITE))

    for part, color in ((part_a, COLOR_PART_A), (part_b, COLOR_PART_B)):
        viewer.scene.add(part.geometry, color=color)
        viewer.scene.add(Tag(text=f"{part.name} ({len(part.features)} feature(s))", position=part.centerline.midpoint, height=25, color=color))

    viewer.scene.add(end_beam.geometry, color=COLOR_END_BEAM)

    viewer.show()


if __name__ == "__main__":
    main()
