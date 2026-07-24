from compas.data import Data
from compas.geometry import Point

from .solver import JointTopology


class JointCandidate(Data):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into Clusters and then promoted
    to concrete joints. Unlike `Joint`, `JointCandidate` is not tied to the joint promotion machinery (features,
    extensions, etc.) and is never registered as a joint on `TimberModel` (`model.joints`) — it lives in its own
    registry (`model.joint_candidates`), added via `TimberModel.add_joint_candidate()`. It mirrors `Joint`'s
    `elements`/`element_guids`/`location` contract closely enough to make that registry symmetrical with `model.joints`.

    Please use `ConnectionSolver.create_joint_candidate()`/`PlateConnectionSolver.create_joint_candidate()` to
    properly create an instance of this class from a pair of adjacent elements.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        First element to be joined.
    element_b : :class:`~compas_model.elements.Element`
        Second element to be joined.
    topology : literal, one of :class:`JointTopology`, optional
        The topology by which the two elements interact. Defaults to `JointTopology.TOPO_UNKNOWN`.
    location : :class:`~compas.geometry.Point`, optional
        The estimated location of the interaction point of the two elements. If not provided, it is calculated
        from the elements' centerlines on first access.
    distance : float, optional
        The distance between the two elements.
    topology_data : tuple(:class:`~compas_timber.connections.TopologyData`, :class:`~compas_timber.connections.TopologyData`), optional
        Structured per-element topology data for `element_a` and `element_b`, respectively.
    name : str, optional
        The name of the candidate.
    element_guids : tuple(str, str), optional
        GUIDs of the two elements, used during deserialization when the live elements aren't available yet.
    **kwargs : dict, optional
        Any additional attributes (e.g. `a_segment_index`, `b_segment_index`) are set directly on the instance.

    Attributes
    ----------
    element_a : :class:`~compas_model.elements.Element`
        First element to be joined.
    element_b : :class:`~compas_model.elements.Element`
        Second element to be joined.
    elements : tuple(:class:`~compas_model.elements.Element`)
        The elements joined by this candidate.
    interactions : list(tuple(:class:`~compas_model.elements.Element`, :class:`~compas_model.elements.Element`))
        The element pairs this candidate connects. This is the minimal surface `TimberModel` needs to store the
        candidate as an edge attribute on its graph.
    topology : literal, one of :class:`JointTopology`
        The topology by which the two elements interact.
    location : :class:`~compas.geometry.Point`
        The estimated location of the interaction point of the two elements.
    distance : float or None
        The distance between the two elements.
    topology_data : tuple(:class:`~compas_timber.connections.TopologyData`, :class:`~compas_timber.connections.TopologyData`) or None
        Structured per-element topology data for `element_a` and `element_b`, respectively.

    """

    def __init__(
        self,
        element_a=None,
        element_b=None,
        topology=None,
        location=None,
        distance=None,
        topology_data=None,
        name=None,
        element_guids=None,
        **kwargs,
    ):
        super(JointCandidate, self).__init__(name=name)
        elements = tuple(e for e in (element_a, element_b) if e is not None)
        if elements:
            self._elements = elements
            self.element_guids = tuple(str(e.guid) for e in elements)
        elif element_guids:
            self._elements = ()
            self.element_guids = tuple(element_guids)
        else:
            raise ValueError("JointCandidate requires either elements or element_guids.")

        self.topology = topology if topology is not None else JointTopology.TOPO_UNKNOWN
        self._location = location
        self.distance = distance
        self.topology_data = topology_data
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def __data__(self):
        return {
            "name": self.name,
            "element_guids": self.element_guids,
            "topology": self.topology,
            "location": self._location,
            "distance": self.distance,
            "topology_data": self.topology_data,
        }

    def __repr__(self):
        return "JointCandidate(element_a={}, element_b={}, topology={})".format(self.element_a, self.element_b, JointTopology.get_name(self.topology))

    @property
    def elements(self):
        return self._elements

    @property
    def element_a(self):
        return self._elements[0] if len(self._elements) > 0 else None

    @property
    def element_b(self):
        return self._elements[1] if len(self._elements) > 1 else None

    @property
    def interactions(self):
        return [(self.element_a, self.element_b)]

    @property
    def location(self):
        if self._location is None and all(self.elements) and len(self.elements) == 2:
            if hasattr(self.elements[0], "centerline"):
                from .joint import location_from_centerlines  # local import: avoids a circular import (joint.py imports JointTopology from solver.py, which imports this module)

                self._location = location_from_centerlines(self.elements)
            else:
                # non-beam elements (e.g. plates) have no centerline-based fallback; match `PlateJoint.location`'s default.
                self._location = Point(0, 0, 0)
        if self._location is None:
            raise ValueError("Location of the joint could not be determined. Please set it manually.")
        return self._location

    @location.setter
    def location(self, value):
        if not isinstance(value, Point):
            raise TypeError("Location must be a Point.")
        self._location = value

    def restore_elements_from_keys(self, model):
        """Restores the reference to the elements associated with this candidate.

        This method is called by :class:`compas_timber.model.TimberModel` during de-serialization to restore the
        references for every candidate in `model.joint_candidates`.

        """
        self._elements = tuple(model[guid] for guid in self.element_guids)

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of this candidate and adds it to `model.joint_candidates`.

        Mirrors :meth:`Joint.create`, except it adds the candidate via `model.add_joint_candidate()` rather than
        `model.add_joint()` — a `JointCandidate` is never registered as an actual joint on the model.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this candidate belong.
        *elements : :class:`~compas_model.elements.Element`
            The elements to be connected by this candidate.
        **kwargs : dict
            Additional keyword arguments that are passed to the candidate's constructor.

        Returns
        -------
        :class:`compas_timber.connections.JointCandidate`
            The instance of the created candidate.

        """
        candidate = cls(*elements, **kwargs)
        model.add_joint_candidate(candidate)
        return candidate
