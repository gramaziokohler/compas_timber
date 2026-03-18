"""Panel wall framing using merge_model.

This example demonstrates how `merge_model` enables a modular design workflow:

1. A main model is built from Panel elements representing the walls of a structure.
2. For each panel, a separate "framing" model is created in the panel's local coordinate
   system (at the origin). This model contains beams representing the timber frame:
   - perimeter beams along the panel edges
   - vertical studs at regular spacing
3. Each framing model is merged into the main model as children of their respective panel.
4. Because the beams are children of the panel in the element tree, they automatically
   inherit the panel's transformation when computing their model-space geometry.

The result: beams that were modeled simply at the origin end up correctly positioned
inside their respective panels in global/model space.

Usage:
    python examples/model/0013_panel_wall_framing.py           # print summary only
    python examples/model/0013_panel_wall_framing.py -v        # open 3D viewer

"""

import argparse
import math

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.model import TimberModel

# ============================================================================
# Configuration
# ============================================================================

PANEL_THICKNESS = 160  # mm (wall thickness / depth of studs)
STUD_SECTION = (40, PANEL_THICKNESS)  # width x height of studs (height matches panel thickness)
STUD_SPACING = 625  # mm, typical on-center spacing


def create_panel_model():
    """Create a simple structure made of four wall panels arranged in a rectangle."""
    model = TimberModel()

    wall_height = 2800  # mm
    length_x = 5000  # mm, walls along X axis
    length_y = 3000  # mm, walls along Y axis

    # Wall 1: along +X axis, at Y=0
    p1 = Panel(
        frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 0, 1)),
        length=length_x,
        width=wall_height,
        thickness=PANEL_THICKNESS,
    )
    p1.name = "wall_south"

    # Wall 2: along +Y axis, at X=length_x
    p2 = Panel(
        frame=Frame(Point(length_x, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)),
        length=length_y,
        width=wall_height,
        thickness=PANEL_THICKNESS,
    )
    p2.name = "wall_east"

    # Wall 3: along -X axis, at Y=length_y (faces inward)
    p3 = Panel(
        frame=Frame(Point(length_x, length_y, 0), Vector(-1, 0, 0), Vector(0, 0, 1)),
        length=length_x,
        width=wall_height,
        thickness=PANEL_THICKNESS,
    )
    p3.name = "wall_north"

    # Wall 4: along -Y axis, at X=0 (faces inward)
    p4 = Panel(
        frame=Frame(Point(0, length_y, 0), Vector(0, -1, 0), Vector(0, 0, 1)),
        length=length_y,
        width=wall_height,
        thickness=PANEL_THICKNESS,
    )
    p4.name = "wall_west"

    for panel in [p1, p2, p3, p4]:
        model.add_element(panel)

    return model


def create_framing_model(panel_length, panel_width, stud_spacing=STUD_SPACING):
    """Create a framing model at the origin for a panel with the given dimensions.

    The framing is built in the panel's local coordinate system:
        x -> panel length direction
        y -> panel width (wall height) direction
        z -> panel thickness direction

    The framing consists of:
        - Bottom rail:   beam along x at y=0
        - Top rail:      beam along x at y=panel_width
        - Left stud:     beam along y at x=0
        - Right stud:    beam along y at x=panel_length
        - Interior studs: beams along y at regular spacing

    All beams are centered on z = panel_thickness / 2 so they sit inside the panel.

    Parameters
    ----------
    panel_length : float
        Length of the panel (x direction).
    panel_width : float
        Width of the panel (y / wall height direction).
    stud_spacing : float
        On-center spacing of vertical studs.

    Returns
    -------
    :class:`TimberModel`

    """
    model = TimberModel()
    stud_w, stud_h = STUD_SECTION

    z_mid = PANEL_THICKNESS / 2.0  # center beams in the thickness

    # -- horizontal rails (along x) ----------------------------------------------------------
    bottom_rail = Beam(
        Frame(Point(0, 0, z_mid), Vector(1, 0, 0), Vector(0, 1, 0)),
        length=panel_length,
        width=stud_w,
        height=stud_h,
    )
    bottom_rail.name = "bottom_rail"

    top_rail = Beam(
        Frame(Point(0, panel_width, z_mid), Vector(1, 0, 0), Vector(0, 1, 0)),
        length=panel_length,
        width=stud_w,
        height=stud_h,
    )
    top_rail.name = "top_rail"

    model.add_element(bottom_rail)
    model.add_element(top_rail)

    # -- vertical studs (along y) -------------------------------------------------------------
    # first and last stud at the edges, then interior studs at regular spacing
    num_bays = max(1, math.floor(panel_length / stud_spacing))
    actual_spacing = panel_length / num_bays
    stud_positions = [i * actual_spacing for i in range(num_bays + 1)]

    for i, x in enumerate(stud_positions):
        stud = Beam(
            Frame(Point(x, 0, z_mid), Vector(0, 1, 0), Vector(1, 0, 0)),
            length=panel_width,
            width=stud_w,
            height=stud_h,
        )
        stud.name = "stud_{}".format(i)
        model.add_element(stud)

    # model.connect_adjacent_beams()

    # for candidate in model.joint_candidates:
    #     beam_a, beam_b = candidate.elements
    #     if candidate.topology == JointTopology.TOPO_T:
    #         TButtJoint.create(model, beam_a, beam_b)
    #     elif candidate.topology == JointTopology.TOPO_L:
    #         LButtJoint.create(model, beam_a, beam_b)

    # model.process_joinery()
    return model


# ============================================================================
# Main
# ============================================================================


def build_model():
    """Build the full framed-wall model by merging framing into panels."""
    panel_model = create_panel_model()

    for panel in list(panel_model.panels):
        framing = create_framing_model(panel.length, panel.width)
        panel_model.merge_model(framing, parent=panel)

    return panel_model


def print_summary(model):
    """Print a quick summary of the model."""
    print("=" * 60)
    print("Panel Wall Framing Model")
    print("=" * 60)
    print("  Panels: {}".format(len(model.panels)))
    print("  Beams:  {}".format(len(model.beams)))
    print("  Total elements: {}".format(len(list(model.elements()))))
    print()

    for panel in model.panels:
        children = panel.treenode.children
        beam_children = [c.element for c in children if isinstance(c.element, Beam)]
        print("  {} ({:.0f} x {:.0f} mm): {} beams".format(panel.name, panel.length, panel.width, len(beam_children)))

        # Verify that beams are positioned in model space (not at origin)
        for child in beam_children[:1]:  # just check the first beam
            model_frame = child.frame
            print(
                "    first beam '{}' model-space origin: ({:.0f}, {:.0f}, {:.0f})".format(
                    child.name,
                    model_frame.point.x,
                    model_frame.point.y,
                    model_frame.point.z,
                )
            )

    print()
    print("Beams were modeled at the origin but appear at the panel locations")
    print("in model space thanks to the transformation chain.")
    print("=" * 60)


def visualize(model):
    """Open an interactive 3D viewer showing panels and framing."""
    from compas_viewer.viewer import Viewer

    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [12000.0, 12000.0, 8000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"

    # Draw panels as semi-transparent boxes
    for panel in model.panels:
        assert panel.geometry
        viewer.scene.add(panel.geometry, opacity=0.15)

    # Draw beam geometry
    for beam in model.beams:
        assert beam.geometry
        viewer.scene.add(beam.geometry)

    # Draw beam centerlines for clarity
    for beam in model.beams:
        viewer.scene.add(beam.centerline, linewidth=2)

    viewer.show()


def main():
    parser = argparse.ArgumentParser(description="Panel wall framing using merge_model")
    parser.add_argument("--visualize", "-v", action="store_true", help="Open 3D viewer")
    args = parser.parse_args()

    model = build_model()
    print_summary(model)

    if args.visualize:
        visualize(model)


if __name__ == "__main__":
    main()
