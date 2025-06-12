from typing import List

from compas.geometry import KDTree
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.model import TimberModel


class Cluster(object):
    """
    one result of an analyzer, groups together the clustered joints and offers access to the beams
    """

    pass


class BeamGroupAnalyzer(object):
    def find(self, exclude=None):
        """Returns a list of beam groups (each group is a list of beams)"""
        raise NotImplementedError


class NBeamKDTreeAnalyzer(BeamGroupAnalyzer):
    """Finds clusters of N beams connected pairwise at the same point within a given tolerance."""

    def __init__(self, model, n=2, tolerance=None):
        super(NBeamKDTreeAnalyzer, self).__init__()
        self.graph = model.graph
        self._joints = list(model.joints)
        self._kdtree = KDTree([joint.location for joint in self._joints])
        self._n = n
        self._tolerance = tolerance or TOL

    def find(self, exclude=None) -> List[Cluster]:
        exclude = exclude or set()  # TODO: uuid clusters so that they can be excluded
        tol = self._tolerance.absolute
        visited = set()
        clusters = []
        for index, joint in enumerate(self._joints):
            if index in visited:
                continue

            result = []
            result.append(joint)
            visited.add(index)

            neighbors = self._kdtree.nearest_neighbors(joint.location, self._n, distance_sort=True)
            for _, idx, distance in neighbors[: self._n]:
                if idx in visited or distance > tol:
                    continue

                result.append(self._joints[idx])
                visited.add(idx)

            if len(result) == self._n:
                clusters.append(result)

        return clusters


def TripletAnalyzer(model, tolerance=None):
    # type: (TimberModel, Tolerance | None) -> BeamGroupAnalyzer
    return NBeamKDTreeAnalyzer(model, n=3, tolerance=tolerance)


def QuadAnalyzer(model, tolerance=None):
    # type: (TimberModel, Tolerance | None) -> BeamGroupAnalyzer
    return NBeamKDTreeAnalyzer(model, n=4, tolerance=tolerance)


class CompositeAnalyzer:
    def __init__(self, analyzers):
        self.analyzers = analyzers

    def find(self):
        exclude = set()
        results = []

        for analyzer in self.analyzers:
            groups = analyzer.find(exclude=exclude)
            for group in groups:
                exclude.update(group)
            results.extend(groups)

        return results
