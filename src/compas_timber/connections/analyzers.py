import math

import compas.geometry
import compas.tolerance  # noqa: F401
import compas_model.elements  # noqa: F401
from compas.geometry import KDTree
from compas.tolerance import TOL

import compas_timber.connections  # noqa: F401
import compas_timber.elements  # noqa: F401
from compas_timber.connections import JointTopology


class Cluster(object):
    """One result of an analyzer, groups together the clustered joints and offers access to the beams

    Parameters
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The joints that are part of this cluster.

    Attributes
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The joints that are part of this cluster.
    elements : set[:class:`~compas_timber.elements.Element`]
        List of unique instances of elements that are part of this cluster.
    location : :class:`~compas.geometry.Point`
        The approximated location of the cluster, effectively the location of the first joint.
    """

    def __init__(self, joints):
        self.joints = joints
        self._elements = None

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    @property
    def elements(self):
        # type: () -> set[compas_model.elements.Element]
        if not self._elements:
            self._elements = set()
            for joint in self.joints:
                self._elements.update(joint.elements)
        return self._elements

    @property
    def location(self):
        # type: () -> compas.geometry.Point
        return self.joints[0].location

    @property
    def topology(self):
        """Returns the topology of the joint if there is only one joint, otherwise TOPO_UNKNOWN."""
        # TODO: will we ever have clusters from non-GenericJoints? if so then we could have a joint in a cluster with TOPO_Y or TOPO_K
        # TOPO_Y + TOPO_I = TOPO_Y
        # TOPO_Y + TOPO_L = TOPO_Y
        # TOPO_Y + TOPO_T = TOPO_K
        # TOPO_K + TOPO_I = TOPO_K
        # TOPO_K + TOPO_L = TOPO_K ...
        if len(self.joints) == 0:
            return JointTopology.TOPO_UNKNOWN
        if len(self.joints) == 1:
            return self.joints[0].topology
        if any([j.topology not in [JointTopology.TOPO_L, JointTopology.TOPO_I, JointTopology.TOPO_T, JointTopology.TOPO_X] for j in self.joints]):
            return JointTopology.TOPO_UNKNOWN
        if any([j.topology == JointTopology.TOPO_T or j.topology == JointTopology.TOPO_X for j in self.joints]):
            return JointTopology.TOPO_K
        return JointTopology.TOPO_Y


class BeamGroupAnalyzer(object):
    """Interface for a beam group analyzer."""

    def find(self, exclude=None):
        """Finds clusters of beams connected pairwise at the same point within a given max_distance."""
        raise NotImplementedError


class NBeamKDTreeAnalyzer(BeamGroupAnalyzer):
    """Finds clusters of N beams connected pairwise at the same point within a given max_distance.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The TimberModel to analyze.
    n : int
        The desired cluster size, i.e. the number of beams in a cluster.
    max_distance : float | None
        The max distance to use for the analysis. If None, a default max distance is used.
    """

    def __init__(self, model, n=2, max_distance=None):
        super(NBeamKDTreeAnalyzer, self).__init__()
        self._joints = list(model.joint_candidates)
        if not self._joints:
            raise ValueError("The model has no joint candidates to analyze. Forgot to call `model.connect_adjacent_beams()`?")

        self._kdtree = KDTree([joint.location for joint in self._joints])
        self._n = n
        self.max_distance = max_distance or TOL.absolute

        # TODO: add parameter to specify groupwise clustering, i.e only look at joints of elements within the same group

    def find(self, exclude=None):
        """Finds clusters of N beams connected pairwise at the same point within a given tolerance.

        Parameters
        ----------
        exclude : set[:class:`~compas_timber.connections.Joint`] | None
            A set of joints to exclude from the analysis. Defaults to None.

        Returns
        -------
        clusters : list[:class:`Cluster`]
            A list of clusters found in the model. Each cluster contains joints that are connected pairwise at the same point.
        """
        # type: (set[compas_timber.connections.Joint] | None) -> list[Cluster]
        exclude = exclude or set()  # TODO: uuid clusters so that they can be excluded
        visited = set()
        neighbors_count = math.comb(self._n, 2) + 1  # +1 for the joint itself
        clusters = []

        for index, joint in enumerate(self._joints):
            if index in visited or joint in exclude:
                continue

            result = []
            result.append(joint)
            visited.add(index)

            neighbors = self._kdtree.nearest_neighbors(joint.location, neighbors_count, distance_sort=True)
            for _, idx, distance in neighbors:
                if idx is None or idx in visited or distance > self.max_distance or idx == index:
                    continue

                n_joint = self._joints[idx]

                result.append(n_joint)
                visited.add(idx)

            # TODO: should we take triplets from e.g. quads as well? AKA clusters.append(result[:self._n])
            if len(result) == neighbors_count - 1:
                clusters.append(Cluster(result))

        return clusters


def TripletAnalyzer(model, max_distance=None):
    """Finds clusters of 3 beams connected pairwise at the same point within a given max_distance."""
    # type: (compas_timber.model.TimberModel, float | None) -> BeamGroupAnalyzer
    return NBeamKDTreeAnalyzer(model, n=3, max_distance=max_distance)


def QuadAnalyzer(model, max_distance=None):
    """Finds clusters of 4 beams connected pairwise at the same point within a given max_distance."""
    # type: (compas_timber.model.TimberModel, float | None) -> BeamGroupAnalyzer
    return NBeamKDTreeAnalyzer(model, n=4, max_distance=max_distance)


class CompositeAnalyzer:
    """CompositeAnalyzer combines multiple analyzers to find clusters of beams.

    Parameters
    ----------
    analyzers : list[BeamGroupAnalyzer]
        A list of analyzers to use for finding clusters.

    Notes
    -----
    Prefer using :meth:`CompositeAnalyzer.from_model` to create an instance, to avoid error-prone manual instantiation.
    Element pairs handled by a previous analyzer will be excluded from subsequent analyzers.

    """

    def __init__(self, analyzers):
        self._analyzers = analyzers

    def find(self, exclude=None):
        """Finds clusters of beams using all analyzers in the composite.

        Parameters
        ----------
        exclude : set[:class:`~compas_timber.connections.Joint`] | None
            A set of joints to exclude from the analysis. Defaults to None.
        """
        exclude = exclude or set()
        results = []

        for analyzer in self._analyzers:
            clusters = analyzer.find(exclude=exclude)
            for cluster in clusters:
                exclude.update(cluster.joints)
            results.extend(clusters)

        return results

    @classmethod
    def from_model(cls, model, analyzers_cls, max_distance=None):
        """Create a CompositeAnalyzer from a TimberModel and a list of analyzers.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The TimberModel to analyze.
        analyzers_cls : list[type[BeamGroupAnalyzer]] | type[BeamGroupAnalyzer]
            A list of analyzer classes to use for finding clusters.
        max_distance : float | None
            The max distance to use for the analysis. If None, a default max distance is used.

        Returns
        -------
        CompositeAnalyzer
            An instance of CompositeAnalyzer with the specified analyzers.
        """
        if not isinstance(analyzers_cls, list):
            analyzers_cls = [analyzers_cls]
        return cls([analyzer(model, max_distance=max_distance) for analyzer in analyzers_cls])


def MaxNCompositeAnalyzer(model, n, max_distance=None):
    """Finds clusters of up to n beams (minimum 2), preferring larger clusters first.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The TimberModel to analyze.
    n : int
        The maximum cluster size.
    max_distance : float | None
        The max distance to use for the analysis. If None, a default max distance is used.

    Returns
    -------
    CompositeAnalyzer
        An instance of CompositeAnalyzer that finds clusters of size n down to 2.
    """
    analyzers_cls = [lambda m, t, k=k: NBeamKDTreeAnalyzer(m, n=k, max_distance=t) for k in range(n, 1, -1)]
    # Use lambdas to capture k at each step
    return CompositeAnalyzer([cls(model, max_distance) for cls in analyzers_cls])
