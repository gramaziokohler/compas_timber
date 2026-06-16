import math

from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import centroid_points
from compas.geometry import intersection_plane_plane_plane
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
    polyhedron : :class:`~compas.geometry.Polyhedron`
        The input polyhedron.

    Returns
    -------
    :class:`~compas.geometry.Polyhedron`
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
