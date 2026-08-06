from compas.data import Data
from compas.geometry import Point

from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.elements import Plate

from .solver import ConnectionSolver
from .solver import JointTopology
from .solver import PlateConnectionSolver

from .candidate_dispatch import find_solver_for



class JointCandidate(Data):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into a Clusters and then
    promoted to concrete joints.

    Construct one directly and register it with :meth:`~compas_timber.model.TimberModel.add_joint_candidate`, or let
    :func:`~compas_timber.connections.get_connection_candidate` build it for an adjacent pair of elements.

    A `JointCandidate` references a single `TopologyData` instance holding everything a solver determined about the
    connection (topology, distance, location, and per-element data). `location`, `distance`, and `topology` are
    convenience properties that read from this referenced `topology_data`; if a candidate is constructed from bare
    elements without one, `topology_data` is always solved lazily, via the solver registered for the pair's element
    types, on first access — there is no partial/stub construction path.

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
    topology_data : :class:`~compas_timber.connections.TopologyData`
        The topology-analysis result referenced by this candidate.
    topology : literal, one of :class:`JointTopology`
        Shortcut for `topology_data.topology`.
    location : :class:`~compas.geometry.Point`
        Shortcut for `topology_data.location`. Settable — writes through to `topology_data.location`.
    distance : float or None
        Shortcut for `topology_data.distance`.

    Notes
    -----
    Element-type-specific results (a plate's connected edge index, a beam's reference side index, ...) are
    deliberately not exposed here — a `JointCandidate` is type-agnostic. Read them off the per-element entry
    instead, e.g. `candidate.topology_data.data_for(plate).edge_index`.

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
        if len(self.elements) < 2:
            raise ValueError("Cannot get connection_solver: this candidate's elements have not been restored yet.")
        solver_type = find_solver_for(*self.elements)
        if solver_type is None:
            raise ValueError("No connection solver is registered for elements {} and {}.".format(self.element_a, self.element_b))
        return solver_type()

    @property
    def topology_data(self):
        """Returns `topology_data`, solving it lazily via the solver registered for this pair if none exists yet."""
        if self._topology_data is None:
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

    def restore_elements_from_keys(self, model):
        """Restores the reference to the elements associated with this candidate.

        This method is called by :class:`compas_timber.model.TimberModel` during de-serialization to restore the
        references for every candidate in `model.joint_candidates`.

        """
        self._elements = tuple(model[guid] for guid in self.element_guids)
