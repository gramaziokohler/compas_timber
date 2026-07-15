"""Ball-node fastener on a group of 6 beams, with the same tree/graph visualization as ``plate_fasteners.py``.

Six beams radiate from a common node (the +x/+y/+z/-x/-y/-z directions). A ``BallNodeJoint`` builds one fastener for the
whole node: a central ball plus a rod and a plate per beam -- 13 part-elements in total.

The two floating boards make visible how much the model's two data structures grow:

* HIERARCHY TREE    -- root owns the 6 beams and the single Fastener; the Fastener owns all 13 parts as children.
* INTERACTION GRAPH -- the 6 beams form a fully connected cluster (every beam pair shares an edge carrying the joint and
  the fastener guid), while the Fastener and its 13 parts sit as *isolated nodes* -- the fastener only rides on the
  beam<->beam edges by guid reference (dashed blue).

Because there are many parts, per-part labels are dropped automatically; the coloured clouds tell the story.
"""

import math

from compas.colors import Color
from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Sphere
from compas.geometry import Vector
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import BallNodeJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import BallNode
from compas_timber.fasteners import BallNodePlate
from compas_timber.fasteners import BallNodeRod
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import FastenerPart
from compas_timber.model import TimberModel

# ---------------------------------------------------------------------------------------------------------------------
# visual language: one colour + one shape per element role, shared across the real model and both diagrams
# ---------------------------------------------------------------------------------------------------------------------
BEAM_COLOR = Color(0.85, 0.62, 0.32)
FASTENER_COLOR = Color(0.20, 0.47, 0.85)
BALL_COLOR = Color(0.16, 0.40, 0.32)  # the central node
ROD_COLOR = Color(0.25, 0.62, 0.62)  # rods (teal)
PLATE_COLOR = Color(0.35, 0.74, 0.52)  # plates (green)
PART_COLOR = Color(0.32, 0.70, 0.48)  # generic part fallback
ROOT_COLOR = Color(0.55, 0.55, 0.58)

TREE_EDGE_COLOR = Color(0.35, 0.35, 0.38)
GRAPH_EDGE_COLOR = Color(0.15, 0.65, 0.35)
REF_COLOR = Color(0.74, 0.74, 0.76)
TITLE_COLOR = Color(0.1, 0.1, 0.12)


def classify(element):
    """Return the (colour, shape) visual style for an element, keyed on its role and (for parts) its subtype."""
    if isinstance(element, Beam):
        return BEAM_COLOR, "sphere"
    if isinstance(element, BallNode):
        return BALL_COLOR, "box"
    if isinstance(element, BallNodeRod):
        return ROD_COLOR, "box"
    if isinstance(element, BallNodePlate):
        return PLATE_COLOR, "box"
    if isinstance(element, FastenerPart):
        return PART_COLOR, "box"
    if isinstance(element, Fastener):
        return FASTENER_COLOR, "box"
    return ROOT_COLOR, "box"


def add_marker(viewer, center, shape, color, half):
    frame = Frame(center, [1, 0, 0], [0, 1, 0])
    geo = Sphere(half, frame) if shape == "sphere" else Box(half * 2, half * 2, half * 2, frame)
    viewer.scene.add(geo, facecolor=color, show_lines=False, name="marker")


def add_label(viewer, center, text, color, dz=0.0, height=15):
    viewer.scene.add(Tag(text, Point(*center) + Vector(0, 0, dz), color=color, height=height, horizontal_align="center"))


def midpoint(*points):
    n = len(points)
    return Point(sum(p.x for p in points) / n, sum(p.y for p in points) / n, sum(p.z for p in points) / n)


def board_outline(viewer, y_panel, rect):
    xmin, xmax, zmin, zmax = rect
    pts = [
        Point(xmin, y_panel + 0.02, zmin),
        Point(xmax, y_panel + 0.02, zmin),
        Point(xmax, y_panel + 0.02, zmax),
        Point(xmin, y_panel + 0.02, zmax),
        Point(xmin, y_panel + 0.02, zmin),
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
            return midpoint(*[p.frame.point for p in parts])
    return None


# ---------------------------------------------------------------------------------------------------------------------
# the real model (beams + a parametric render of the fastener, so it does not depend on a Brep/OCC backend)
# ---------------------------------------------------------------------------------------------------------------------
def draw_real_model(viewer, model):
    viewer.scene.add(Tag("the real model", Point(0.0, 0.0, -1.35), color=TITLE_COLOR, height=18, horizontal_align="center"))

    for beam in model.beams:
        try:
            viewer.scene.add(beam.geometry, facecolor=BEAM_COLOR, opacity=0.55, name="beam")
        except Exception:
            viewer.scene.add(beam.centerline, linecolor=BEAM_COLOR, linewidth=4)

    for fastener in model.fasteners:
        node_point = fastener.frame.point
        for part in fastener.parts:
            if isinstance(part, BallNode):
                viewer.scene.add(Sphere(part.radius, Frame(node_point, [1, 0, 0], [0, 1, 0])), facecolor=BALL_COLOR, show_lines=False)
            elif isinstance(part, BallNodeRod):
                cylinder = Cylinder(part.diameter / 2, part.length, part.frame.copy())
                cylinder.frame.point += part.frame.zaxis * part.length / 2
                viewer.scene.add(cylinder, facecolor=ROD_COLOR, show_lines=False)
            elif isinstance(part, BallNodePlate):
                box = Box(part.x_size, part.y_size, part.thickness, part.frame.copy())
                box.frame.point += part.frame.zaxis * part.thickness / 2
                viewer.scene.add(box, facecolor=PLATE_COLOR, show_lines=False)


# ---------------------------------------------------------------------------------------------------------------------
# the two data structures, drawn as node-link boards that auto-scale to the number of nodes
# ---------------------------------------------------------------------------------------------------------------------
def draw_tree(viewer, model, y_panel, rect, marker_unit, label_parts):
    board_outline(viewer, y_panel, rect)
    xmin, xmax, zmin, zmax = rect
    viewer.scene.add(Tag("HIERARCHY  TREE", Point((xmin + xmax) / 2, y_panel, zmax + 0.14), color=TITLE_COLOR, height=24, horizontal_align="center"))
    viewer.scene.add(Tag("(containment: parent owns children)", Point((xmin + xmax) / 2, y_panel, zmax + 0.06), color=TITLE_COLOR, height=14, horizontal_align="center"))

    positions = {}
    leaf = [0]

    def layout(node, depth):
        children = node.children
        if not children:
            xf = leaf[0]
            leaf[0] += 1
        else:
            xf = sum(layout(child, depth + 1) for child in children) / len(children)
        positions[node] = (xf, depth)
        return xf

    layout(model.tree.root, 0)
    span = max(leaf[0] - 1, 1)
    max_depth = max(depth for _, depth in positions.values())

    def world(node):
        xf, depth = positions[node]
        wx = xmin + (xf / span) * (xmax - xmin)
        wz = zmax - (depth / max(max_depth, 1)) * (zmax - zmin)
        return Point(wx, y_panel, wz)

    for node in positions:
        for child in node.children:
            viewer.scene.add(Line(world(node), world(child)), linecolor=TREE_EDGE_COLOR, linewidth=2, show_points=False)

    for node in positions:
        center = world(node)
        if node.is_root:
            add_marker(viewer, center, "box", ROOT_COLOR, marker_unit * 0.8)
            add_label(viewer, center, "root", ROOT_COLOR, dz=marker_unit * 2.2)
            continue
        element = node.element
        color, shape = classify(element)
        is_part = isinstance(element, FastenerPart)
        add_marker(viewer, center, shape, color, marker_unit * (0.7 if is_part else 1.0))
        if not is_part or label_parts:
            add_label(viewer, center, type(element).__name__, color, dz=marker_unit * 2.2, height=13)


def draw_graph(viewer, model, y_panel, rect, marker_unit, label_parts):
    graph = model.graph
    board_outline(viewer, y_panel, rect)
    xmin, xmax, zmin, zmax = rect
    viewer.scene.add(Tag("INTERACTION  GRAPH", Point((xmin + xmax) / 2, y_panel, zmax + 0.14), color=TITLE_COLOR, height=24, horizontal_align="center"))
    viewer.scene.add(Tag("(relationships: who interacts with whom)", Point((xmin + xmax) / 2, y_panel, zmax + 0.06), color=TITLE_COLOR, height=14, horizontal_align="center"))

    nodes = list(graph.nodes())
    cx, cz = (xmin + xmax) / 2, (zmin + zmax) / 2
    radius = 0.42 * min(xmax - xmin, zmax - zmin)
    pos = {}
    for i, node in enumerate(nodes):
        angle = math.pi / 2 - 2 * math.pi * i / len(nodes)
        pos[node] = Point(cx + radius * math.cos(angle), y_panel, cz + radius * math.sin(angle))

    edges = list(graph.edges())
    for edge in edges:
        viewer.scene.add(Line(pos[edge[0]], pos[edge[1]]), linecolor=GRAPH_EDGE_COLOR, linewidth=2, show_points=False)

    # with many edges, one summary beats a label per chord
    if edges:
        active = sorted({key for edge in edges for key, value in graph.edge_attributes(edge).items() if value})
        note = "{} beam<->beam edges: {}".format(len(edges), " + ".join(active))
        viewer.scene.add(Tag(note, Point(cx, y_panel, zmin - 0.08), color=GRAPH_EDGE_COLOR, height=14, horizontal_align="center"))

    for node in nodes:
        center = pos[node]
        element = graph.node_element(node)
        color, shape = classify(element)
        is_part = isinstance(element, FastenerPart)
        add_marker(viewer, center, shape, color, marker_unit * (0.7 if is_part else 1.0))
        if not is_part or label_parts:
            add_label(viewer, center, type(element).__name__, color, dz=marker_unit * 2.2, height=13)
        anchor = element_anchor(element)
        if anchor is not None:
            viewer.scene.add(Line(center, anchor), linecolor=REF_COLOR, linewidth=1, show_points=False)

    # the key subtlety: each fastener is an isolated node, yet its guid is referenced on the beam<->beam edges
    for fastener in model.fasteners:
        fastener_node = next(n for n in nodes if graph.node_element(n) is fastener)
        referencing_mids = [midpoint(pos[e[0]], pos[e[1]]) for e in edges if str(fastener.guid) in (graph.edge_attribute(e, "fasteners") or [])]
        if referencing_mids:
            target = midpoint(*referencing_mids)
            viewer.scene.add(Line(pos[fastener_node], target), linecolor=FASTENER_COLOR, linewidth=1, show_points=False)
            add_label(viewer, midpoint(pos[fastener_node], target), "guid on {} edges".format(len(referencing_mids)), FASTENER_COLOR, height=13)


def draw_legend(viewer, y_panel, at):
    x, ztop = at
    entries = [
        ("sphere = Beam", BEAM_COLOR),
        ("cube = Fastener", FASTENER_COLOR),
        ("cube = BallNode / Rod / Plate parts", PLATE_COLOR),
        ("line = tree parent->child", TREE_EDGE_COLOR),
        ("line = graph interaction edge", GRAPH_EDGE_COLOR),
        ("dashed = fastener guid on edges", FASTENER_COLOR),
        ("thin grey = node <-> real element", REF_COLOR),
    ]
    for i, (text, color) in enumerate(entries):
        viewer.scene.add(Tag(text, Point(x, y_panel, ztop - i * 0.16), color=color, height=14, horizontal_align="left"))


def visualize_model(model):
    # derive the board placement from the extent of the real model, so the layout scales with the scene
    pts = []
    for beam in model.beams:
        pts.append(beam.centerline.start)
        pts.append(beam.centerline.end)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    cx = (min(xs) + max(xs)) / 2
    size = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 0.5)

    y_panel = min(ys) - 0.6 * size
    z0 = max(zs) + 0.25 * size
    board_h = 1.1 * size
    board_w = 1.1 * size
    gap = 0.35 * size
    tree_cx = cx - (board_w + gap) / 2
    graph_cx = cx + (board_w + gap) / 2
    tree_rect = (tree_cx - board_w / 2, tree_cx + board_w / 2, z0, z0 + board_h)
    graph_rect = (graph_cx - board_w / 2, graph_cx + board_w / 2, z0, z0 + board_h)
    marker_unit = 0.03 * size

    n_parts = len(model.find_all_elements_of_type(FastenerPart))
    label_parts = n_parts <= 6  # keep dense scenes legible: let the coloured clouds speak instead

    viewer = Viewer()
    viewer.renderer.camera.position = [cx, y_panel - 1.6 * size, z0 + board_h * 0.5]
    viewer.renderer.camera.target = [cx, (min(ys) + y_panel) / 2, (max(zs) + z0 + board_h / 2) / 2]
    viewer.renderer.rendermode = "ghosted"

    draw_real_model(viewer, model)
    draw_tree(viewer, model, y_panel, tree_rect, marker_unit, label_parts)
    draw_graph(viewer, model, y_panel, graph_rect, marker_unit, label_parts)
    draw_legend(viewer, y_panel, (tree_rect[0], z0 + board_h - 0.05))

    viewer.show()


# ---------------------------------------------------------------------------------------------------------------------
# build the model: 6 beams meeting at the origin, joined by a single ball-node fastener
# (the first two beams must not be collinear, since the joint derives the node from their intersection)
# ---------------------------------------------------------------------------------------------------------------------
LENGTH = 1.0
DIRECTIONS = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]

beams = [Beam.from_centerline(Line([0, 0, 0], [d[0] * LENGTH, d[1] * LENGTH, d[2] * LENGTH]), width=0.05, height=0.05) for d in DIRECTIONS]

model = TimberModel()
model.add_elements(beams)

BallNodeJoint.create(model, *beams, ball_diameter=0.12, rods_length=0.15, plate_thickness=0.02, plate_depth=0.1)

model.process_joinery()
model.process_fasteners()

print(model.tree.get_hierarchy_string())

visualize_model(model)
