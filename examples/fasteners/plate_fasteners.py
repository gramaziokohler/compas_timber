"""Plate fastener example, with a live visualization of the two data structures a TimberModel maintains.

Besides the "real" model (two beams + the plate fastener geometry), this draws two floating node-link boards:

* the HIERARCHY TREE  -- who contains whom (root -> beams / fastener -> plate parts)
* the INTERACTION GRAPH -- who relates to whom (the single beam<->beam edge carrying the joint and the fastener guid)

The point it makes visible: once a fastener and its parts became ``Element``s, they are *nodes in both structures*. In the
tree the fastener owns its plate parts as children; in the graph the fastener and its parts sit as isolated nodes, while
the fastener is merely *referenced by guid* on the beam<->beam edge (dashed blue link).
"""

import math

from compas.colors import Color
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Sphere
from compas.geometry import Vector
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import FastenerPart
from compas_timber.fasteners import PlateFastener
from compas_timber.model import TimberModel

# ---------------------------------------------------------------------------------------------------------------------
# visual language: one colour + one shape per element role, shared across the real model and both diagrams
# ---------------------------------------------------------------------------------------------------------------------
BEAM_COLOR = Color(0.85, 0.62, 0.32)
FASTENER_COLOR = Color(0.20, 0.47, 0.85)
PART_COLOR = Color(0.28, 0.70, 0.48)
ROOT_COLOR = Color(0.55, 0.55, 0.58)

TREE_EDGE_COLOR = Color(0.35, 0.35, 0.38)
GRAPH_EDGE_COLOR = Color(0.15, 0.65, 0.35)
REF_COLOR = Color(0.72, 0.72, 0.74)
TITLE_COLOR = Color(0.1, 0.1, 0.12)

# board placement (both boards are billboards in the y = Y_PANEL plane, facing the camera)
Y_PANEL = -0.85
TREE_X0 = -0.25
TREE_COL = 0.38
TREE_ZTOP = 1.28
TREE_ROW = 0.40
GRAPH_CX = 1.72
GRAPH_CZ = 0.92
GRAPH_R = 0.42


def classify(element):
    """Return the (colour, shape, size) visual style for an element, keyed on its role."""
    if isinstance(element, Beam):
        return BEAM_COLOR, "sphere", 0.055
    if isinstance(element, FastenerPart):
        return PART_COLOR, "box", 0.045
    if isinstance(element, Fastener):
        return FASTENER_COLOR, "box", 0.075
    return ROOT_COLOR, "box", 0.05


def add_marker(viewer, center, shape, color, size):
    frame = Frame(center, [1, 0, 0], [0, 1, 0])
    geo = Sphere(size, frame) if shape == "sphere" else Box(size * 2, size * 2, size * 2, frame)
    viewer.scene.add(geo, facecolor=color, show_lines=False, name="marker")


def add_label(viewer, center, text, color, dz=0.07, height=15):
    viewer.scene.add(Tag(text, Point(*center) + Vector(0, 0, dz), color=color, height=height, horizontal_align="center"))


def midpoint(a, b):
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)


def board_outline(viewer, xmin, xmax, zmin, zmax):
    pts = [
        Point(xmin, Y_PANEL + 0.02, zmin),
        Point(xmax, Y_PANEL + 0.02, zmin),
        Point(xmax, Y_PANEL + 0.02, zmax),
        Point(xmin, Y_PANEL + 0.02, zmax),
        Point(xmin, Y_PANEL + 0.02, zmin),
    ]
    viewer.scene.add(Polyline(pts), linecolor=Color(0.82, 0.82, 0.85), linewidth=1, show_points=False)


def element_anchor(element):
    """A representative point on the *real* element, used to tie a graph node back to what it stands for."""
    if isinstance(element, Beam):
        return element.centerline.midpoint
    if isinstance(element, FastenerPart):
        return element.frame.point
    if isinstance(element, Fastener):
        parts = list(element.parts)
        if parts:
            pts = [p.frame.point for p in parts]
            return Point(sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), sum(p.z for p in pts) / len(pts))
    return None


def draw_tree(viewer, model):
    """Draw the containment hierarchy as a top-down node-link diagram: root at the top, parts at the bottom."""
    board_outline(viewer, TREE_X0 - 0.25, 1.05, 0.35, 1.5)
    viewer.scene.add(Tag("HIERARCHY  TREE", Point(0.35, Y_PANEL, 1.6), color=TITLE_COLOR, height=26, horizontal_align="center"))
    viewer.scene.add(Tag("(containment: parent owns children)", Point(0.35, Y_PANEL, 1.52), color=TITLE_COLOR, height=15, horizontal_align="center"))

    positions = {}
    leaf_counter = [0]

    def layout(node, depth):
        children = node.children
        if not children:
            xf = leaf_counter[0]
            leaf_counter[0] += 1
        else:
            xf = sum(layout(child, depth + 1) for child in children) / len(children)
        positions[node] = (xf, depth)
        return xf

    root = model.tree.root
    layout(root, 0)

    def world(node):
        xf, depth = positions[node]
        return Point(TREE_X0 + xf * TREE_COL, Y_PANEL, TREE_ZTOP - depth * TREE_ROW)

    # parent -> child links first, so markers draw on top
    for node in positions:
        for child in node.children:
            viewer.scene.add(Line(world(node), world(child)), linecolor=TREE_EDGE_COLOR, linewidth=2, show_points=False)

    for node in positions:
        center = world(node)
        if node.is_root:
            add_marker(viewer, center, "box", ROOT_COLOR, 0.04)
            add_label(viewer, center, "root", ROOT_COLOR)
        else:
            element = node.element
            color, shape, size = classify(element)
            add_marker(viewer, center, shape, color, size)
            add_label(viewer, center, type(element).__name__, color)


def draw_graph(viewer, model):
    """Draw the interaction graph as a circular node-link diagram; edges carry the interaction attributes."""
    graph = model.graph
    board_outline(viewer, 1.15, 2.3, 0.35, 1.5)
    viewer.scene.add(Tag("INTERACTION  GRAPH", Point(GRAPH_CX, Y_PANEL, 1.6), color=TITLE_COLOR, height=26, horizontal_align="center"))
    viewer.scene.add(Tag("(relationships: who interacts with whom)", Point(GRAPH_CX, Y_PANEL, 1.52), color=TITLE_COLOR, height=15, horizontal_align="center"))

    nodes = list(graph.nodes())
    pos = {}
    for i, node in enumerate(nodes):
        angle = math.pi / 2 + 2 * math.pi * i / len(nodes)
        pos[node] = Point(GRAPH_CX + GRAPH_R * math.cos(angle), Y_PANEL, GRAPH_CZ + GRAPH_R * math.sin(angle))

    # interaction edges + their attribute labels
    for edge in graph.edges():
        a, b = pos[edge[0]], pos[edge[1]]
        active = [key for key, value in graph.edge_attributes(edge).items() if value]
        viewer.scene.add(Line(a, b), linecolor=GRAPH_EDGE_COLOR, linewidth=4, show_points=False)
        add_label(viewer, midpoint(a, b), " + ".join(active), GRAPH_EDGE_COLOR, dz=0.04, height=14)

    # nodes, their labels, and a faint tie-line back to the real element each node stands for
    for node in nodes:
        center = pos[node]
        element = graph.node_element(node)
        color, shape, size = classify(element)
        add_marker(viewer, center, shape, color, size)
        add_label(viewer, center, type(element).__name__, color)
        anchor = element_anchor(element)
        if anchor is not None:
            viewer.scene.add(Line(center, anchor), linecolor=REF_COLOR, linewidth=1, show_points=False)

    # the key subtlety: a fastener is an isolated node, yet it is *referenced by guid* on the beam<->beam edge
    for edge in graph.edges():
        referenced = graph.edge_attribute(edge, "fasteners") or []
        edge_mid = midpoint(pos[edge[0]], pos[edge[1]])
        for node in nodes:
            element = graph.node_element(node)
            if str(element.guid) in referenced:
                viewer.scene.add(Line(pos[node], edge_mid), linecolor=FASTENER_COLOR, linewidth=1, show_points=False)
                add_label(viewer, midpoint(pos[node], edge_mid), "guid on edge", FASTENER_COLOR, dz=0.03, height=13)


def draw_legend(viewer):
    entries = [
        ("sphere = Beam", BEAM_COLOR),
        ("cube = Fastener", FASTENER_COLOR),
        ("cube = FastenerPart", PART_COLOR),
        ("line = tree parent->child", TREE_EDGE_COLOR),
        ("line = graph interaction edge", GRAPH_EDGE_COLOR),
        ("dashed = fastener guid on edge", FASTENER_COLOR),
        ("thin grey = node <-> real element", REF_COLOR),
    ]
    for i, (text, color) in enumerate(entries):
        viewer.scene.add(Tag(text, Point(-0.5, Y_PANEL, 1.25 - i * 0.11), color=color, height=14, horizontal_align="left"))


def visualize_model(model):
    viewer = Viewer()
    viewer.renderer.camera.position = [1.0, -3.4, 1.5]
    viewer.renderer.camera.target = [1.0, -0.2, 0.65]
    viewer.renderer.rendermode = "ghosted"

    # the real model, colour-coded by role, sitting on the ground plane
    viewer.scene.add(Tag("the real model", Point(1.0, 0.5, 0.2), color=TITLE_COLOR, height=18, horizontal_align="center"))
    for beam in model.beams:
        viewer.scene.add(beam.geometry, facecolor=BEAM_COLOR, opacity=0.6, name="beam")
    for fastener in model.fasteners:
        for geometry in fastener.geometry:
            viewer.scene.add(geometry, facecolor=PART_COLOR, name="plate")

    # the two data structures, side by side above the model
    draw_tree(viewer, model)
    draw_graph(viewer, model)
    draw_legend(viewer)

    viewer.show()


cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [1, 1, 0]), width=0.05, height=0.05)


model = TimberModel()
model.add_elements([cross_beam, main_beam])


# Create the joint
joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True, conical_tool=True)


# WHAT: a joint-agnostic plate fastener
fastener = PlateFastener(width=0.04, height=0.05, thickness=0.005, recess=0.005, recess_offset=0.001)

# WHERE: the joint publishes its attachment anchors; the fastener binds to the ones it accepts
anchors = joint.fastener_anchors.of_kind(AnchorKind.FACE)
fastener.bind(anchors)


model.add_fastener(fastener, joint.beams)
model.process_joinery()
model.process_fasteners()


print(model.tree.get_hierarchy_string())

visualize_model(model)
