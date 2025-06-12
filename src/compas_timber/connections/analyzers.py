import math
from typing import List

from compas.geometry import KDTree
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.connections import Joint
from compas_timber.model import TimberModel


class Cluster(object):
    """
    one result of an analyzer, groups together the clustered joints and offers access to the beams
    """

    def __init__(self, joints):
        self.joints = joints

    @property
    def elements(self):
        return set([joint.element for joint in self.joints])


class BeamGroupAnalyzer(object):
    def find(self, exclude=None):
        """Returns a list of beam groups (each group is a list of beams)"""
        raise NotImplementedError


class NBeamKDTreeAnalyzer(BeamGroupAnalyzer):
    """Finds clusters of N beams connected pairwise at the same point within a given tolerance."""

    # TODO: add parameter to specify groupwise clustering, i.e only look at joints of elements within the same group
    def __init__(self, model, n=2, tolerance=None):
        super(NBeamKDTreeAnalyzer, self).__init__()
        self._joints = list(model.joints)
        if not self._joints:
            raise ValueError("The model has no joints to analyze.")

        self.graph = model.graph
        self._kdtree = KDTree([joint.location for joint in self._joints])
        self._n = n
        self._tolerance = tolerance or TOL

    def find(self, exclude=None) -> List[Cluster]:
        # type: (list(Joint) | None) -> list(Cluster)
        exclude = exclude or set()  # TODO: uuid clusters so that they can be excluded
        tol = self._tolerance.absolute
        visited = set()
        neighbors_count = math.comb(self._n, 2) + 1  # +1 for the joint itself
        clusters = []

        for index, joint in enumerate(self._joints):
            print(f"analyzing joint {[e.graph_node for e in joint.elements]}")
            if index in visited:
                print("skipping already visited joint")
                continue

            result = []
            result.append(joint)
            visited.add(index)

            neighbors = self._kdtree.nearest_neighbors(joint.location, neighbors_count, distance_sort=True)

            for _, idx, distance in neighbors:
                n_joint = self._joints[idx]
                n_joint_id = [e.graph_node for e in n_joint.elements]
                print(f"inspecting neighbor: {n_joint_id}")

                if idx in visited or distance > tol or idx == index:
                    print("skipping visited neighbor")
                    continue
                print(f"adding neighbor to result: {n_joint_id}")
                result.append(n_joint)
                visited.add(idx)

            print(f"finished cluster with {len(result)} joints")
            # TODO: should we take triplets from e.g. quads as well? AKA clusters.append(result[:self._n])
            if len(result) == neighbors_count - 1:
                print("adding cluster")
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

    def find(self, exclude=None):
        exclude = exclude or set()
        results = []

        for analyzer in self.analyzers:
            groups = analyzer.find(exclude=exclude)
            exclude.update([g.joints for g in groups])
            results.extend(groups)

        return results
