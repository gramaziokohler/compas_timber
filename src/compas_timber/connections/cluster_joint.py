from __future__ import annotations

from typing import TYPE_CHECKING

from .cluster import Cluster
from .joint import Joint
from .solver import JointTopology

if TYPE_CHECKING:
    from compas_timber.model import TimberModel


class ClusterJoint(Joint):
    """A joint composed of multiple pairwise sub-joints acting on a cluster of 3 or more elements.

    Instead of defining a single fabrication strategy for the whole cluster, this joint
    delegates all feature and extension calculations to a list of pairwise sub-joints.
    The sub-joints are instantiated without being registered in the model; only the
    ClusterJoint itself is added.

    Parameters
    ----------
    cluster : :class:`~compas_timber.connections.Cluster`
        The cluster of elements connected by this joint.
    name : str, optional
        The name of the joint.

    Attributes
    ----------
    cluster : :class:`~compas_timber.connections.Cluster`
        The cluster connected by this joint.
    joints : list[:class:`~compas_timber.connections.Joint`]
        The pairwise sub-joints.
    elements : tuple[:class:`~compas_timber.elements.Element`]
        The unique elements connected by this joint, derived from the sub-joints.
    location : :class:`~compas.geometry.Point`
        The approximate location of the joint, taken from the `cluster.location`.
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the joint, taken from the `cluster.topology`.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = None

    def __init__(self, cluster, name=None, **kwargs):
        self.cluster = cluster
        elements = cluster.elements
        super(ClusterJoint, self).__init__(elements=elements, name=name, **kwargs)

    @property
    def __data__(self):
        data = super().__data__
        data["cluster"] = self.cluster
        return data

    def __repr__(self):
        return "{}({} sub-joints)".format(self.__class__.__name__, len(self.joints))

    @property
    def location(self):
        """The approximate location of the joint, taken from the first sub-joint."""
        return self.cluster.location

    @property
    def topology(self):
        """Returns the topology of the joint if there is only one joint, otherwise TOPO_UNKNOWN."""
        return self.cluster.topology

    @property
    def joints(self):
        """The cluster of elements connected by this joint."""
        return self.cluster.joints

    @property
    def features(self):
        """Delegates feature calculation to each sub-joint and returns a combined list of features."""
        features = []
        for joint in self.joints:
            features.extend(joint.features)
        return features

    @features.setter
    def features(self, value):
        # feature storage is delegated to the sub-joints, nothing to store here.
        pass

    @classmethod
    def create(cls, model, cluster, **kwargs):
        """Creates a ClusterJoint and registers it in the model.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to register this joint in.
        cluster : :class:`~compas_timber.connections.Cluster`
            The Cluster object.

        Returns
        -------
        :class:`~compas_timber.connections.ClusterJoint`
        """
        joint = cls(cluster=cluster, **kwargs)
        model.add_joint(joint)
        return joint

    @classmethod
    def promote_cluster(cls, model, cluster, **kwargs):
        """Creates an instance of this joint from a cluster of elements.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster containing the pairwise joints held by this joint.
        **kwargs : dict
            Additional keyword arguments that are passed to the joint's constructor.

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """
        return cls.create(model, cluster, **kwargs)

    def add_features(self):
        """Delegates feature calculation to each sub-joint."""
        for joint in self.joints:
            joint.add_features()

    def add_extensions(self):
        """Delegates extension calculation to each sub-joint."""
        for joint in self.joints:
            joint.add_extensions()

    def clear_features(self):
        """Delegates feature removal to each sub-joint."""
        for joint in self.joints:
            joint.clear_features()

    def clear_extensions(self):
        """Delegates feature removal to each sub-joint."""
        for joint in self.joints:
            joint.clear_extensions()

    def restore_elements_from_keys(self, model: TimberModel):
        """Restores element references by delegating to each sub-joint, then rebuilds elements.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model from which to look up elements by GUID.
        """
        for joint in self.joints:
            joint.restore_elements_from_keys(model)
            joint._set_unset_attributes()
        self._elements = tuple(set([e for j in self.joints for e in j.elements]))

    @classmethod
    def from_joints(cls, joints: list[Joint]) -> ClusterJoint:
        """
        Creates a ClusterJoint from a list of pairwise sub-joints.
        Parameters
        ----------
        joints : list[:class:`~compas_timber.connections.Joint`]
            The list of pairwise sub-joints to be included in the cluster joint.

        Returns
        -------
        :class:`compas_timber.connections.ClusterJoint`
        """
        cluster = Cluster(joints)
        return cls(cluster=cluster)
