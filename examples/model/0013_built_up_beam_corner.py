"""Built-up beam corner example.

This script demonstrates a ``CompositeBeam`` whose cross-section is genuinely built up
from multiple layers, extruded along the beam's length - not a planar frame with gaps
between them, like a ladder or a truss. Looking down the beam's own length axis, the
cross-section is:

      Y (edge-spacing) -->
    +----+--------+----+
    |    |  top   |    |   ^
    | left  middle right |  | Z (stacking)
    |    |        |    |  |
    |    | bottom |    |   v
    +----+--------+----+

All 5 layers - left/right edge beams and bottom/middle/top beams - are plain ``Beam``
elements, stacked/side-by-side, all running the *full length* of the composite. (An
earlier version of this example used ``Plate`` for the two edge layers, matching the
red/yellow reference sketch more literally - see the note at the bottom about why that
version's edges couldn't be mitered by the same joint used for the beams.)

Two such composites are built - one along X, one along Y - meeting at a right-angle
corner, and joined with a single ordinary ``LMiterJoint.create(model, composite_a,
composite_b)`` call. Both composites are built with ``cut_all_parts=True``, so
``TimberModel.process_joinery`` doesn't just route that one joint to a single nearest
part (the default - see ``0012_composite_beam.py`` for that case) - it clones it once
per matching pair of parts (left-left, bottom-bottom, middle-middle, top-top,
right-right), so *every* layer gets its own miter cut. ``LMiterJoint`` itself needs no
``CompositeBeam``-awareness at all.

Why not keep the edges as ``Plate``: ``LMiterJoint`` is a ``Beam``-oriented joint type
(it calls ``.centerline``/``.ref_sides``, which ``Plate`` doesn't implement) - so
``_expand_composite_joints`` silently skips any pair involving a ``Plate``. Giving
``Plate`` edges an equivalent cut needs a plate-aware joint type - ``PlateMiterJoint``
exists in the codebase, but its automatic edge-detection didn't succeed on this
composite's plates when tried, and that hasn't been root-caused yet. Using ``Beam`` for
all 5 layers sidesteps that open question entirely.

A note on a real gotcha hit while building this: once a part is added to a composite via
``add_part``, its frame is interpreted *relative to the composite's own frame* - exactly
like any other parent/child pair in the model tree. The earlier composite-beam examples
never surfaced this because their composite's own frame happened to be the world
identity. Here, both composites have a genuinely offset/rotated frame, so every part's
frame below is explicitly converted from world coordinates via
``composite_frame.to_local_coordinates(...)`` before construction.

Run this script from the repository root::

    python examples/model/0013_built_up_beam_corner.py

"""

import os

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import LMiterJoint
from compas_timber.elements import Beam
from compas_timber.elements import CompositeBeam
from compas_timber.model import TimberModel

HERE = os.path.dirname(__file__)

ARM_A_LENGTH = 1500
ARM_B_LENGTH = 1000
STACK_HEIGHT = 300  # the edge beams' extent along the stacking (Z) axis - the full cross-section height
EDGE_BEAM_WIDTH = 40  # the left/right edge beams' extent along the edge-spacing (Y) axis
CLEAR_SPAN = 120  # the bottom/middle/top beams' extent along the edge-spacing axis, between the edges
BEAM_HEIGHT = 100  # each of the bottom/middle/top beams' extent along the stacking (Z) axis
CROSS_SECTION_WIDTH = 2 * EDGE_BEAM_WIDTH + CLEAR_SPAN  # edge-spacing axis, outer to outer

# ----- colours: outer edge beams vs. inner span beams -----
COLOR_EDGE_BEAM = Color.from_hex("#F4A0A0")
COLOR_SPAN_BEAM = Color.from_hex("#F4E97A")


def _cross_section_layers(composite_frame, length):
    """Builds the 5 Beam layers of one arm's built-up cross-section, all in world coordinates,
    then converts each to a frame local to *composite_frame* before construction.

    *composite_frame* is the composite's own nominal envelope, positioned at the cross-section's
    center (coinciding with the middle beam layer) - so layer offsets are computed from the
    cross-section's corner (w=0, h=0), which sits half a cross-section away from that center.
    """

    def local(world_frame):
        return composite_frame.to_local_coordinates(world_frame)

    x_axis = composite_frame.xaxis  # the arm's length direction
    y_axis = composite_frame.yaxis  # the arm's edge-spacing direction
    z_axis = x_axis.cross(y_axis)  # the arm's stacking direction - constant across both arms
    corner = composite_frame.point - y_axis * (CROSS_SECTION_WIDTH / 2) - z_axis * (STACK_HEIGHT / 2)

    def at(y, z):
        return corner + y_axis * y + z_axis * z

    left_beam = Beam(local(Frame(at(EDGE_BEAM_WIDTH / 2, STACK_HEIGHT / 2), x_axis, y_axis)), length=length, width=EDGE_BEAM_WIDTH, height=STACK_HEIGHT)
    right_beam = Beam(local(Frame(at(CROSS_SECTION_WIDTH - EDGE_BEAM_WIDTH / 2, STACK_HEIGHT / 2), x_axis, y_axis)), length=length, width=EDGE_BEAM_WIDTH, height=STACK_HEIGHT)

    span_y_center = CROSS_SECTION_WIDTH / 2
    bottom_beam = Beam(local(Frame(at(span_y_center, BEAM_HEIGHT / 2), x_axis, y_axis)), length=length, width=CLEAR_SPAN, height=BEAM_HEIGHT)
    middle_beam = Beam(local(Frame(at(span_y_center, STACK_HEIGHT / 2), x_axis, y_axis)), length=length, width=CLEAR_SPAN, height=BEAM_HEIGHT)
    top_beam = Beam(local(Frame(at(span_y_center, STACK_HEIGHT - BEAM_HEIGHT / 2), x_axis, y_axis)), length=length, width=CLEAR_SPAN, height=BEAM_HEIGHT)

    return left_beam, right_beam, bottom_beam, middle_beam, top_beam


def build_model():
    # ------------------------------------------------------------------
    # 1. Build both composites' nominal envelopes to coincide with their own
    #    middle beam layer - so that's what the external LMiterJoint resolves to.
    #    Arm A runs along X, arm B along Y, both stacking (Z) the same way.
    # ------------------------------------------------------------------
    corner = Point(ARM_A_LENGTH, CROSS_SECTION_WIDTH / 2, STACK_HEIGHT / 2)
    composite_a_frame = Frame(Point(0, CROSS_SECTION_WIDTH / 2, STACK_HEIGHT / 2), Vector(1, 0, 0), Vector(0, 1, 0))
    composite_b_frame = Frame(corner, Vector(0, 1, 0), Vector(-1, 0, 0))

    # cut_all_parts=True: the miter joint below applies to every one of the 5 Beam layers,
    # not just the one nearest the composite's own nominal envelope.
    composite_a = CompositeBeam(composite_a_frame, length=ARM_A_LENGTH, width=CLEAR_SPAN, height=BEAM_HEIGHT, cut_all_parts=True)
    composite_b = CompositeBeam(composite_b_frame, length=ARM_B_LENGTH, width=CLEAR_SPAN, height=BEAM_HEIGHT, cut_all_parts=True)

    layers_a = _cross_section_layers(composite_a_frame, ARM_A_LENGTH)
    layers_b = _cross_section_layers(composite_b_frame, ARM_B_LENGTH)
    for name, part in zip(("left_beam", "right_beam", "bottom_beam", "middle_beam", "top_beam"), layers_a):
        part.name = name + "_a"
        composite_a.add_part(part)
    for name, part in zip(("left_beam", "right_beam", "bottom_beam", "middle_beam", "top_beam"), layers_b):
        part.name = name + "_b"
        composite_b.add_part(part)

    # ------------------------------------------------------------------
    # 2. Add to the model.
    # ------------------------------------------------------------------
    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    # ------------------------------------------------------------------
    # 3. Ordinary joint between the two composites, exactly as if they were
    #    plain beams.
    # ------------------------------------------------------------------
    LMiterJoint.create(model, composite_a, composite_b)

    # ------------------------------------------------------------------
    # 4. Resolve joinery.
    # ------------------------------------------------------------------
    errors = model.process_joinery()
    if errors:
        raise RuntimeError("process_joinery reported errors: {}".format(errors))

    return model, composite_a, composite_b, layers_a, layers_b


def main():
    model, composite_a, composite_b, layers_a, layers_b = build_model()

    print(f"Elements in model: {len(list(model.elements()))}")
    print(f"composite_a features: {len(composite_a.features)} (0 expected)")
    print(f"composite_b features: {len(composite_b.features)} (0 expected)")
    for part in layers_a + layers_b:
        joinery_features = [type(f).__name__ for f in part.features if type(f).__name__ != "FreeContour"]
        print(f"  {part.name} ({type(part).__name__}): {joinery_features}")

    # ------------------------------------------------------------------
    # Visualise
    # ------------------------------------------------------------------
    viewer = Viewer()
    corner = composite_b.centerline.start
    viewer.renderer.camera.target = [corner.x, corner.y, corner.z]
    viewer.renderer.camera.position = [corner.x - 2000.0, corner.y - 2500.0, corner.z + 2000.0]
    viewer.renderer.camera.far = 100_000.0
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"

    # Note: composite_a/composite_b themselves are deliberately not drawn here - they stay pure,
    # uncut nominal envelopes (see the docstring), and since each one's own frame coincides with
    # its middle beam layer's position, drawing them would just look like two uncut duplicates
    # sitting on top of middle_beam_a/middle_beam_b.
    for part in layers_a + layers_b:
        color = COLOR_EDGE_BEAM if "left" in part.name or "right" in part.name else COLOR_SPAN_BEAM
        viewer.scene.add(part.geometry, color=color)
        viewer.scene.add(Tag(text=f"{part.name} ({len(part.features)})", position=part.aabb.frame.point, height=18, color=color))

    viewer.show()


if __name__ == "__main__":
    main()
