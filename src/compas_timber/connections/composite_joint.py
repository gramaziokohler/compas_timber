from __future__ import annotations

from typing import TYPE_CHECKING

from .cluster import Cluster
from .joint import Joint
from .solver import JointTopology

if TYPE_CHECKING:
    from compas_timber.model import TimberModel


class CompositeJoint(Joint):
    """A joint composed of multiple pairwise sub-joints acting on a cluster of 3 or more elements.

    Instead of defining a single fabrication strategy for the whole cluster, this joint
    delegates all feature and extension calculations to a list of pairwise sub-joints.
    The sub-joints are instantiated without being registered in the model; only the
    CompositeJoint itself is added.

    Parameters
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The pairwise sub-joints that make up this composite connection. These joints must not be added to model.
    name : str, optional
        The name of the joint.
    cluster : :class:`~compas_timber.connections.Cluster`, optional
        The cluster of elements connected by this joint. If not provided, it will be created from `joints`.

    Attributes
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The pairwise sub-joints.
    elements : tuple[:class:`~compas_timber.elements.Element`]
        The unique elements connected by this joint, derived from the sub-joints.
    cluster : :class:`~compas_timber.connections.Cluster`
        The cluster of elements connected by this joint.
    location : :class:`~compas.geometry.Point`
        The approximate location of the joint, taken from the `cluster.location`.
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the joint, taken from the `cluster.topology`.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = None

    def __init__(self, joints, name=None, cluster=None, **kwargs):
        self.joints = joints
        self._cluster = cluster
        elements = list(set([e for j in joints for e in j.elements]))
        super(CompositeJoint, self).__init__(elements=elements, name=name, **kwargs)

    @property
    def __data__(self):
        data = super().__data__
        data["joints"] = self.joints
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
    def cluster(self):
        """The cluster of elements connected by this joint."""
        if self._cluster is None:
            self._cluster = Cluster(self.joints)
        return self._cluster

    @property
    def features(self):
        """Delegates feature calculation to each sub-joint and returns a combined list of features."""
        features = []
        for joint in self.joints:
            features.extend(joint.features)
        return features

    @classmethod
    def create(cls, model, joints=None, **kwargs):
        """Creates a CompositeJoint and registers it in the model.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to register this joint in.
        joints : list[:class:`~compas_timber.connections.Joint`], optional
            The pairwise sub-joints.

        Returns
        -------
        :class:`~compas_timber.connections.CompositeJoint`
        """
        joint = cls(joints=joints, **kwargs)
        model.add_joint(joint)
        return joint

    def add_features(self):
        """Delegates feature calculation to each sub-joint."""
        for joint in self.joints:
            joint.add_features()

    def add_extensions(self):
        """Delegates extension calculation to each sub-joint."""
        for joint in self.joints:
            joint.add_extensions()

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
