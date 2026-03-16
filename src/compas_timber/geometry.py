import math

from scipy.spatial import KDTree as _ScipyKDTree


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

    def query_pairs(self, max_distance) -> list[tuple[int,int]]:
        """returns a list of pairs of indices of points in the tree that are within *max_distance* of each other."""
        return self._tree.query_pairs(max_distance)
