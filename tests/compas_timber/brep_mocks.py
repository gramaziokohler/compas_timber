"""Minimal duck-typed Brep stubs for unit tests.

These objects implement only the interface that ``mesh_from_brep_simple``,
``get_plate_geometry_outlines_from_brep``, and ``polylines_from_brep_face``
actually traverse:

    brep.faces → face.loops → loop.is_outer, loop.edges
    edge.start_vertex.point, edge.end_vertex.point
    brep.vertices → v.point

No Rhino/OCC plugin is required.
"""


class MockVertex:
    """Brep vertex stub."""

    def __init__(self, point):
        self.point = point


class MockEdge:
    """Brep edge stub (straight line from start to end)."""

    def __init__(self, start_point, end_point):
        self.start_vertex = MockVertex(start_point)
        self.end_vertex = MockVertex(end_point)


class MockLoop:
    """Brep loop stub."""

    def __init__(self, edges, is_outer=True):
        self.edges = edges
        self.is_outer = is_outer


class MockFace:
    """Brep face stub containing a single outer loop."""

    def __init__(self, pts):
        n = len(pts)
        edges = [MockEdge(pts[i], pts[(i + 1) % n]) for i in range(n)]
        self.loops = [MockLoop(edges, is_outer=True)]


class MockBrep:
    """Minimal Brep stub compatible with ``mesh_from_brep_simple`` and related utils."""

    def __init__(self, faces, all_vertices):
        self.faces = faces
        self.vertices = [MockVertex(p) for p in all_vertices]


def make_single_face_brep(pts):
    """Return a single-face :class:`MockBrep` from an ordered list of Points."""
    return MockBrep(faces=[MockFace(pts)], all_vertices=pts)


def make_plate_brep(pts_a, pts_b):
    """Return a closed prismatic :class:`MockBrep` from two parallel polygon outlines.

    Produces one face per polygon (bottom/top) plus one quad side face per edge,
    matching the topology expected by ``get_plate_geometry_outlines_from_brep``.

    Parameters
    ----------
    pts_a : list[:class:`~compas.geometry.Point`]
        Vertices of the first (bottom) face in order.
    pts_b : list[:class:`~compas.geometry.Point`]
        Vertices of the second (top) face in order, same count as *pts_a*.

    Returns
    -------
    :class:`MockBrep`
    """
    n = len(pts_a)
    all_pts = list(pts_a) + list(pts_b)

    faces = [
        MockFace(pts_a),  # bottom
        MockFace(pts_b),  # top
    ]
    for i in range(n):
        j = (i + 1) % n
        # side quad: a[i], a[j], b[j], b[i]
        faces.append(MockFace([pts_a[i], pts_a[j], pts_b[j], pts_b[i]]))

    return MockBrep(faces=faces, all_vertices=all_pts)
