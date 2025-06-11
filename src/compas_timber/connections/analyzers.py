from typing import List
from compas.geometry import KDTree


class Cluster:
    """
    one result of an analyzer, groups together the clustered joints and offers access to the beams
    """

    pass


class BeamGroupAnalyzer(object):
    def __init__(self, model):
        self.model = model
        self.graph = model.graph
        self.analyzed = set()  # Beams already included in groups

    def find(self, exclude=None):
        """Returns a list of beam groups (each group is a list of beams)"""
        raise NotImplementedError


class TripletAnalyzer(BeamGroupAnalyzer):
    def __init__(self, model):
        super(TripletAnalyzer, self).__init__(model)
        self.graph = model.graph
        self._joints = list(model.joints)
        self._kdtree = KDTree([joint.location for joint in self._joints])

    def find(self, exclude=None, tol=1e-6) -> List[Cluster]:
        exclude = exclude or set()

        visited = set()
        clusters = []
        for index, joint in enumerate(self._joints):
            if index in visited:
                continue

            result = []
            result.append(joint)
            visited.add(index)

            # Find 3 nearby joints within tolerance
            neighbors = self._kdtree.nearest_neighbors(joint.location, 3, distance_sort=True)
            for _, idx, distance in neighbors[:3]:
                if idx in visited or distance > tol:
                    continue

                result.append(self._joints[idx])
                visited.add(idx)

            if len(result) == 3:
                clusters.append(result)

        return clusters


class PairAnalyzer(BeamGroupAnalyzer):
    def find(self, exclude=None):
        exclude = exclude or set()
        results = []

        for u, v in self.graph.edges():
            if u in exclude or v in exclude:
                continue
            results.append([u, v])
            exclude.update([u, v])

        return results


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
