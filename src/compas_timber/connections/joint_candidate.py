from compas.data import Data
from compas.geometry import Point

from .candidate_dispatch import find_connection_handler
from .solver import JointTopology


class JointCandidate(Data):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into a Clusters and then
    promoted to concrete joints.

    Please use `JointCandidate.create()` to properly create an instance of this class and associate it with a model.

    A `JointCandidate` references a single `TopologyData` instance holding everything a solver determined about the
    connection (topology, distance, location, and per-element data). `location`, `distance`, and `topology` are
    convenience properties that read from this referenced `topology_data`; if a candidate is constructed from bare
    elements without one, `topology_data` is always solved lazily, via the connection handler registered for the
    pair's element types, on first access — there is no partial/stub construction path.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        First element to be joined.
    element_b : :class:`~compas_model.elements.Element`
        Second element to be joined.
    topology_data : :class:`~compas_timber.connections.TopologyData`, optional
        The topology-analysis result for this pair of elements. If not provided, it is computed lazily
        from the elements on first access to `location`, `distance`, or `topology`.
    name : str, optional
        The name of the candidate.
    element_guids : tuple(str, str), optional
        GUIDs of the two elements, used during deserialization when the live elements aren't available yet.
    **kwargs : dict, optional
        Any additional attributes are set directly on the instance.

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
    solver : :class:`~compas_timber.connections.ConnectionSolver` or None
        The solver registered for this candidate's pair of element types, or ``None`` if unsupported.
    topology_data : :class:`~compas_timber.connections.TopologyData` or None
        The topology-analysis result referenced by this candidate.
    topology : literal, one of :class:`JointTopology`
        Shortcut for `topology_data.topology`.
    location : :class:`~compas.geometry.Point`
        Shortcut for `topology_data.location`. Settable — writes through to `topology_data.location`.
    distance : float or None
        Shortcut for `topology_data.distance`.
    a_segment_index : int or None
        Shortcut for `topology_data.data_for(element_a).edge_index`.
    b_segment_index : int or None
        Shortcut for `topology_data.data_for(element_b).edge_index`.

    """

    def __init__(
        self,
        element_a=None,
        element_b=None,
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

        # backward compatibility: older serialized models flattened topology/location/distance directly
        # onto JointCandidate instead of nesting them in a `topology_data`; drop them silently on load
        # rather than crashing -- they get recomputed lazily via `topology_data` on first access anyway.
        kwargs.pop("topology", None)
        kwargs.pop("location", None)
        kwargs.pop("distance", None)

        self._topology_data = topology_data
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def __data__(self):
        return {
            "name": self.name,
            "element_guids": self.element_guids,
            "topology_data": self._topology_data,
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
    def solver(self):
        handler_type = find_connection_handler(*self.elements)
        return handler_type() if handler_type is not None else None

    @property
    def topology_data(self):
        """Returns `topology_data`, solving it lazily via the registered connection handler if none exists yet."""
        if self._topology_data is None:
            if len(self.elements) < 2:
                raise ValueError("Location of the joint could not be determined. Please set it manually.")
            self._topology_data = self.solver.find_topology(*self.elements)
        return self._topology_data

    @property
    def location(self):
        return self.topology_data.location

    @location.setter
    def location(self, value):
        if not isinstance(value, Point):
            raise TypeError("Location must be a Point.")
        self.topology_data.location = value

    @property
    def distance(self):
        return self.topology_data.distance

    @property
    def topology(self):
        return self.topology_data.topology

    @property
    def a_segment_index(self):
        data = self.topology_data.data_for(self.element_a) if self.topology_data else None
        return data.edge_index if data else None

    @property
    def b_segment_index(self):
        data = self.topology_data.data_for(self.element_b) if self.topology_data else None
        return data.edge_index if data else None

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
