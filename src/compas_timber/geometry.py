import math
from typing import List
from typing import Optional

from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Polyhedron
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import centroid_points
from compas.geometry import distance_point_point
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL
from compas_brep import Brep
from scipy.spatial import KDTree as _ScipyKDTree

from compas_timber.utils import is_polyline_clockwise


# TODO: perhaps this should be the canonical implementation of KDTree in core, scipy is already a dependency anyways.
class KDTree:
    """Wrapper around :class:`scipy.spatial.KDTree` that mimics the :class:`compas.geometry.KDTree` interface.

    Parameters
    ----------
    points : list[:class:`~compas.geometry.Point`]
        The points to build the tree from.
    """

    def __init__(self, points):
        self._points = list(points)
        self._tree = _ScipyKDTree([[p[0], p[1], p[2]] for p in self._points])

    def nearest_neighbors(self, point, num, distance_sort=True):
        """Return the *num* nearest neighbours of *point*.

        Parameters
        ----------
        point : :class:`~compas.geometry.Point`
            The query point.
        num : int
            The number of neighbours to return.
        distance_sort : bool, optional
            Unused - scipy always returns results sorted by distance.

        Returns
        -------
        list[tuple[:class:`~compas.geometry.Point` | None, int | None, float]]
            Each entry is ``(point_or_None, index_or_None, distance)``.
            When fewer than *num* points are in the tree the missing entries
            carry ``None`` for both point and index and ``math.inf`` for
            distance, matching the :class:`compas.geometry.KDTree` contract.
        """
        k = min(num, len(self._points))
        if k == 0:
            return [(None, None, math.inf)] * num

        distances, indices = self._tree.query([point[0], point[1], point[2]], k=k)

        # scipy returns bare scalars when k == 1
        if k == 1:
            distances = [distances]
            indices = [indices]

        results = []
        for d, i in zip(distances, indices):
            if math.isinf(d):
                results.append((None, None, d))
            else:
                results.append((self._points[i], int(i), float(d)))

        # Pad with None entries if fewer points than requested
        while len(results) < num:
            results.append((None, None, math.inf))

        return results

    def query_pairs(self, max_distance) -> list[tuple[int, int]]:
        """returns a list of pairs of indices of points in the tree that are within *max_distance* of each other."""
        return self._tree.query_pairs(max_distance)


def polyhedron_from_box_planes(top_plane, bottom_plane, side_a_plane, side_b_plane, end_a_plane, end_b_plane):
    """Create a hexahedral :class:`~compas.geometry.Polyhedron` defined by 6 bounding planes.

    The geometry is equivalent to the intersection of three pairs of half-spaces.
    Vertices are computed as all 8 triple-plane intersections from the two top/bottom
    planes, two side planes, and two end planes.

    Parameters
    ----------
    top_plane : :class:`~compas.geometry.Plane`
        The plane forming the top face of the hexahedron.
    bottom_plane : :class:`~compas.geometry.Plane`
        The plane forming the bottom face of the hexahedron.
    side_a_plane : :class:`~compas.geometry.Plane`
        The plane forming one lateral side of the hexahedron.
    side_b_plane : :class:`~compas.geometry.Plane`
        The plane forming the opposite lateral side of the hexahedron.
    end_a_plane : :class:`~compas.geometry.Plane`
        The plane forming one end face of the hexahedron.
    end_b_plane : :class:`~compas.geometry.Plane`
        The plane forming the opposite end face of the hexahedron.

    Returns
    -------
    :class:`~compas.geometry.Polyhedron`
        A hexahedral polyhedron with 8 vertices and 6 faces.

    """
    vertices = [
        Point(*intersection_plane_plane_plane(top_plane, side_a_plane, end_a_plane)),
        Point(*intersection_plane_plane_plane(top_plane, side_a_plane, end_b_plane)),
        Point(*intersection_plane_plane_plane(top_plane, side_b_plane, end_b_plane)),
        Point(*intersection_plane_plane_plane(top_plane, side_b_plane, end_a_plane)),
        Point(*intersection_plane_plane_plane(bottom_plane, side_a_plane, end_a_plane)),
        Point(*intersection_plane_plane_plane(bottom_plane, side_a_plane, end_b_plane)),
        Point(*intersection_plane_plane_plane(bottom_plane, side_b_plane, end_b_plane)),
        Point(*intersection_plane_plane_plane(bottom_plane, side_b_plane, end_a_plane)),
    ]
    faces = [[0, 3, 2, 1], [1, 2, 6, 5], [2, 3, 7, 6], [0, 4, 7, 3], [0, 1, 5, 4], [4, 5, 6, 7]]
    return oriented_polyhedron(Polyhedron(vertices=vertices, faces=faces))


def oriented_polyhedron(polyhedron: Polyhedron) -> Polyhedron:
    """Returns the polyhedron with consistently oriented faces.

    This function ensures that the normals of the polyhedron's faces are all
    oriented outwards by reordering the vertex indices that define each face.

    Parameters
    ----------
    polyhedron :
        The input polyhedron.

    Returns
    -------
        A new polyhedron with its faces reordered to ensure outward-facing normals.

    """
    vertices = [Point(*vertex) for vertex in polyhedron.vertices]
    faces = polyhedron.faces

    if not vertices or not faces:
        raise ValueError("The polyhedron must have vertices and faces to ensure outward-facing normals.")

    poly_centroid = Point(*centroid_points(vertices))
    new_faces = []
    for face in faces:
        face_centroid = centroid_points([vertices[i] for i in face])
        outward = Vector.from_start_end(poly_centroid, face_centroid)

        polyline = Polyline([vertices[i] for i in face])
        clockwise = is_polyline_clockwise(polyline, outward)

        if not clockwise:
            new_faces.append(list(face))
        else:
            new_faces.append(list(reversed(face)))

    polyhedron.faces = new_faces
    return polyhedron


def _without_repeated_points(polyline: Polyline) -> Polyline:
    points = polyline.points
    return Polyline([point for i, point in enumerate(points) if i == 0 or not TOL.is_allclose(point, points[i - 1])])


# BTLx stores coordinates to three decimals, so an outline read from a BTLx file may lie off its plane by about that much
OUTLINE_FLATNESS_TOLERANCE = 0.002


def _flattened(outline: Polyline, name: str) -> Polyline:
    """The closed `outline` with its points moved onto its plane, as OCC builds faces only from points which lie in one.

    Raises a ValueError if any of them lies further off it than `OUTLINE_FLATNESS_TOLERANCE`, or a millionth of the
    outline's size if that is more.

    """
    points = outline.points[:-1]
    normal = Polygon(points).normal
    center = Point(*centroid_points(points))
    size = max(distance_point_point(center, point) for point in points)
    offsets = [Vector.from_start_end(center, point).dot(normal) for point in points]
    if max(abs(offset) for offset in offsets) > max(1e-6 * size, OUTLINE_FLATNESS_TOLERANCE):
        raise ValueError("{} is not planar.".format(name))
    flat = [point - normal * offset for point, offset in zip(points, offsets)]
    return Polyline(flat + [flat[0]])


def _planar_faces(points: List[Point]) -> List[List[Point]]:
    """The side face through four points, or two triangles if they do not quite lie in one plane, as happens between
    outlines on planes which are not parallel, read from a BTLx file."""
    if len(points) == 4:
        normal = Vector.from_start_end(points[0], points[1]).cross(Vector.from_start_end(points[0], points[2]))
        if normal.length > 1e-12 and abs(Vector.from_start_end(points[0], points[3]).dot(normal.unitized())) > 1e-7:
            return [points[:3], [points[0], points[2], points[3]]]
    return [points]


def brep_from_outlines(outline_a: Polyline, outline_b: Polyline, normal: Optional[Vector] = None) -> Brep:
    """Create a solid brep from two closed outlines.

    Assumes outline_a and outline_b are closed planar polylines with the same number of vertices. Their planes need not
    be parallel, as the bottom of a DualContour may be tilted, but they must face the same way: each pair of
    corresponding segments makes a side face. An outline a little off its plane, as one read from a BTLx file, whose
    coordinates are rounded, is moved onto it, and a side face whose corners then do not quite lie in one plane is made of
    two triangles.

    Parameters
    ----------
    outline_a :
        The first closed outline.
    outline_b :
        The second closed outline.
    normal :
        The normal vector around which the outlines are oriented.

    Returns
    -------
        A Brep representing the solid defined by the two outlines.

    Raises
    ------
    ValueError
        If either outline is not closed, if the outlines don't have the same
        number of vertices, if either is not planar, or if the outlines are square to each other.
    """
    if not TOL.is_allclose(outline_a[0], outline_a[-1]):
        raise ValueError("outline_a is not closed: its first and last points must coincide.")
    if not TOL.is_allclose(outline_b[0], outline_b[-1]):
        raise ValueError("outline_b is not closed: its first and last points must coincide.")
    if len(outline_a) != len(outline_b):
        raise ValueError("outline_a and outline_b must have the same number of vertices.")

    outline_a = _flattened(outline_a, "outline_a")
    outline_b = _flattened(outline_b, "outline_b")
    normal_a = Polygon(outline_a.points[:-1]).normal
    normal_b = Polygon(outline_b.points[:-1]).normal
    if abs(normal_a.dot(normal_b)) < 1e-3:
        raise ValueError("outline_a and outline_b are square to each other: they do not bound a solid between them.")

    normal = normal or Vector(0, 0, 1)
    # the direction is told from the distinct points: a repeated point would make a segment without direction
    if not is_polyline_clockwise(_without_repeated_points(outline_a), normal):
        outline_a = Polyline(outline_a[::-1])
    if not is_polyline_clockwise(_without_repeated_points(outline_b), normal):
        outline_b = Polyline(outline_b[::-1])

    vector_a = Vector.from_start_end(outline_a[0], outline_b[0])
    if vector_a.dot(normal) < 0:
        # make sure that outline_b is above (Z+) outline_a
        outline_a, outline_b = outline_b, outline_a

    faces = [outline_a.points[0:-1], outline_b.points[-2::-1]]
    for i in range(len(outline_a) - 1):
        faces.append([outline_a[i], outline_b[i], outline_b[i + 1], outline_a[i + 1]])
    # an outline may repeat a point, where a segment of the other one has no counterpart: its side face is a triangle
    polygons = []
    for points in faces:
        distinct = [p for i, p in enumerate(points) if not TOL.is_allclose(p, points[i - 1])]
        if len(distinct) >= 3:
            polygons.extend(Polygon(face) for face in _planar_faces(distinct))
    return Brep.from_polygons(polygons)


def _first_solid(results: List[Brep], operation: str) -> Brep:
    # taking the first piece is not a meaningful selection, it is what the Rhino backend happened to do
    # internally in compas.geometry.Brep. Which piece is wanted is a decision only the caller can make, so a
    # caller which can tell them apart should call the boolean operation directly and select from all of them.
    if not results:
        raise IndexError("Boolean {} left no result.".format(operation))
    return results[0]


def brep_difference_first(brep_a: Brep, brep_b: Brep) -> Brep:
    """Subtracts `brep_b` from `brep_a` and returns the first resulting piece.

    Parameters
    ----------
    brep_a :
        The Brep to subtract from.
    brep_b :
        The Brep to subtract.

    Returns
    -------
        The first resulting piece.

    Raises
    ------
    IndexError
        If nothing is left of `brep_a` after the subtraction.

    """
    return _first_solid(Brep.from_boolean_difference(brep_a, brep_b), "difference")


def brep_union_first(brep_a: Brep, *breps: Brep) -> Brep:
    """Unions `brep_a` with one or more other Breps and returns the first resulting piece.

    Parameters
    ----------
    brep_a :
        The Brep to union with.
    *breps :
        One or more Breps to union with `brep_a`.

    Returns
    -------
        The first resulting piece.

    Raises
    ------
    IndexError
        If the union left no result.

    """
    if not breps:
        raise ValueError("At least one Brep to union with is required.")
    return _first_solid(Brep.from_boolean_union_multi(brep_a, *breps), "union")


def brep_intersection_first(brep_a: Brep, brep_b: Brep) -> Brep:
    """Intersects `brep_a` with `brep_b` and returns the first resulting piece.

    Parameters
    ----------
    brep_a :
        The first Brep.
    brep_b :
        The second Brep.

    Returns
    -------
        The first resulting piece.

    Raises
    ------
    IndexError
        If the two Breps do not overlap.

    """
    return _first_solid(Brep.from_boolean_intersection(brep_a, brep_b), "intersection")


def brep_edge_indices_not_parallel_to_plane(brep: Brep, plane: Plane) -> List[int]:
    """Returns the indices of the straight edges of `brep` which are not parallel to `plane`.

    Selects edges by their direction rather than by their position in ``brep.edges``, which depends on the backend.
    For a box built on `plane`, these are the four edges along the box's height. The indices can be passed to
    :meth:`compas_brep.Brep.fillet`.

    Parameters
    ----------
    brep :
        The Brep whose edges are selected.
    plane :
        The plane the selected edges are not parallel to.

    Returns
    -------
        The indices of the selected edges in ``brep.edges``.

    """
    normal = plane.normal.unitized()
    indices = []
    for index, edge in enumerate(brep.edges):
        if not edge.is_line:
            continue
        direction = Vector.from_start_end(edge.start_vertex.point, edge.end_vertex.point).unitized()
        if not TOL.is_zero(direction.dot(normal), tol=TOL.angular):
            indices.append(index)
    return indices


def brep_from_box_with_rounded_corners(box: Box, radius: float) -> Brep:
    """Creates a Brep from `box` with the corners of its cross-section rounded, e.g. a round tenon or mortise.

    The cross-section is the box's xy-plane, so the rounded corners are the four edges along its z-axis. When `radius`
    is half the smaller side of the cross-section, the rounded corners meet, which a fillet cannot produce. The Brep is
    then built from cylinders instead: a cylinder for a square cross-section, otherwise a box with two half-cylinder ends,
    whose top and bottom faces stay split where the pieces were joined.

    Parameters
    ----------
    box :
        The box whose corners are rounded.
    radius :
        The radius of the rounded corners. At most half the smaller side of the cross-section.

    Returns
    -------
        The box with rounded corners.

    Raises
    ------
    ValueError
        If `radius` is larger than half the smaller side of the cross-section.

    """
    half_side = min(box.xsize, box.ysize) / 2.0
    if TOL.is_close(radius, half_side):
        return _brep_stadium_from_box(box)
    if radius > half_side:
        raise ValueError("Radius {} is larger than half the smaller side of the box's cross-section ({}).".format(radius, half_side))
    brep = Brep.from_box(box)
    brep.fillet(radius, brep_edge_indices_not_parallel_to_plane(brep, Plane.from_frame(box.frame)))
    return brep


def _brep_stadium_from_box(box: Box) -> Brep:
    # rounds the cross-section of the box with half its smaller side, so the rounded corners meet
    frame = box.frame
    radius = min(box.xsize, box.ysize) / 2.0
    if TOL.is_close(box.xsize, box.ysize):
        return Brep.from_cylinder(Cylinder(radius, box.zsize, frame))
    if box.xsize > box.ysize:
        axis = frame.xaxis
        core = Box(box.xsize - 2.0 * radius, box.ysize, box.zsize, frame)
    else:
        axis = frame.yaxis
        core = Box(box.xsize, box.ysize - 2.0 * radius, box.zsize, frame)
    offset = max(box.xsize, box.ysize) / 2.0 - radius
    ends = [Brep.from_cylinder(Cylinder(radius, box.zsize, Frame(frame.point + axis * (offset * side), frame.xaxis, frame.yaxis))) for side in (-1, 1)]
    return brep_union_first(Brep.from_box(core), *ends)
