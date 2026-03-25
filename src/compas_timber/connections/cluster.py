from collections import defaultdict

from compas.geometry import Point
from compas.tolerance import TOL
from compas_model.elements import Element

from compas_timber.connections import JointTopology
from compas_timber.geometry import KDTree


class Cluster(object):
    """Groups together the clustered joints and offers access to the beams

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
    def elements(self) -> set[Element]:
        if not self._elements:
            self._elements = set()
            for joint in self.joints:
                self._elements.update(joint.elements)
        return self._elements

    @property
    def location(self) -> Point:
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


def get_clusters_from_model(model, max_distance=None, exclude=None):
    """Gets a sorted list of Cluster objects from a model's JointCandidates
    run model.connect_adjacent_beams() first to populate the model's joint_candidates

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        TimberModel whose joint_candidates should be clustered.
    max_distance : float
        Maximum distance between joints to be considered co-located.
    exclude : set[Joint] | None
        Joints to exclude from clustering.

    Returns
    -------
    list[Cluster]
        Clusters sorted largest-first.
    """

    max_distance = max_distance or TOL.absolute
    exclude = exclude or set()
    active_joints = [joint for joint in model.joint_candidates if joint not in exclude]
    active_joints.sort(key=lambda j: j.location[0])  # ensure a deterministic order for caching and testing)
    if not active_joints:
        return []

    kd_tree = KDTree([j.location for j in active_joints])

    # Get all pairs of joints whose distance is within max_distance.
    # TODO: upstream to compas.geometry.KDTree and kd_tree.query_pairs(max_distance)

    # Each joint starts as its own cluster, represented by its own index as root.
    cluster_index_per_joint = list(range(len(active_joints)))

    def get_cluster_index(joint_index):
        # if value is the index, then the joint's cluster index is the joint_index (that joint is cluster root)
        while cluster_index_per_joint[joint_index] != joint_index:
            # set this joint's cluster index to the cluster it points to.
            cluster_index_per_joint[joint_index] = cluster_index_per_joint[cluster_index_per_joint[joint_index]]
            joint_index = cluster_index_per_joint[joint_index]
        return joint_index

    def merge_clusters(joint_index_a, joint_index_b):
        cluster_index_a = get_cluster_index(joint_index_a)
        cluster_index_b = get_cluster_index(joint_index_b)
        if cluster_index_a != cluster_index_b:
            cluster_index_per_joint[cluster_index_b] = cluster_index_a

    joint_pairs = kd_tree.query_pairs(max_distance)
    for joint_index_a, joint_index_b in joint_pairs:
        merge_clusters(joint_index_a, joint_index_b)

    joints_by_cluster_index = defaultdict(list)
    for joint_index, joint in enumerate(active_joints):
        joints_by_cluster_index[get_cluster_index(joint_index)].append(joint)

    grouped_joints = sorted(joints_by_cluster_index.values(), key=len, reverse=True)

    return [Cluster(joint_group) for joint_group in grouped_joints]
