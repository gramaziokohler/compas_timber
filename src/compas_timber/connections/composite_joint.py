from __future__ import annotations

from typing import TYPE_CHECKING

from compas.geometry import Point

from .cluster import get_topology_from_joints
from .joint import Joint
from .solver import JointTopology

if TYPE_CHECKING:
    from compas_timber.model import TimberModel


class CompositeJoint(Joint):
    """A joint composed of multiple pairwise sub-joints.

    Instead of defining a single fabrication strategy for all joined elements, this joint
    delegates all feature and extension calculations to a list of pairwise sub-joints.
    The sub-joints are instantiated without being registered in the model; only the
    CompositeJoint itself is added.

    Parameters
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The joints contained by this joint.
    name : str, optional
        The name of the joint.

    Attributes
    ----------
    joints : list[:class:`~compas_timber.connections.Joint`]
        The pairwise sub-joints.
    elements : tuple[:class:`~compas_timber.elements.Element`]
        The unique elements connected by this joint, derived from the sub-joints.
    location : :class:`~compas.geometry.Point`
        The approximate location of the joint, the average of the `self.joints` locations.
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the joint, composed from the individual `self.joints` topologies.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = None

    def __init__(self, joints: list[Joint], name: str = None, **kwargs):
        self.joints = joints
        kwargs["name"] = name
        kwargs["location"] = sum([j.location for j in joints], Point(0, 0, 0)) / len(joints)
        kwargs["topology"] = get_topology_from_joints(joints)
        kwargs["elements"] = tuple(set([e for j in joints for e in j.elements]))
        super(CompositeJoint, self).__init__(**kwargs)

    @property
    def __data__(self):
        data = super().__data__
        data["joints"] = self.joints
        return data

    def __repr__(self):
        return "{}({} sub-joints)".format(self.__class__.__name__, len(self.joints))

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
