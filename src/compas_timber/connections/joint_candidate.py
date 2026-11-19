from compas.data import Data
from compas.geometry import Point

from .solver import JointTopology
from .topology_info import TopologyInfo


class JointCandidate(Data):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into a Clusters and then
    promoted to concrete joints.

    A candidate is element-type agnostic: everything it knows about the connection (topology, distance,
    location and the per-element role/end/edge info) lives in a single
    :class:`~compas_timber.connections.TopologyInfo`, as computed by the connection solver registered for
    the elements' types in :mod:`compas_timber.connections.candidate_dispatch`.

    Please use `JointCandidate.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    topology_info : :class:`~compas_timber.connections.TopologyInfo`, optional
        The topology info of the connection. If not provided, it is solved on first access by the
        connection solver registered for the elements' types.
    topology : literal, one of :class:`JointTopology`, optional
        Shortcut to set `topology_info.topology` when `topology_info` is not given.
    location : :class:`~compas.geometry.Point`, optional
        Shortcut to set `topology_info.location` when `topology_info` is not given.
    distance : float, optional
        Shortcut to set `topology_info.distance` when `topology_info` is not given.
    name : str, optional
        The name of the candidate.
    element_guids : tuple(str, str), optional
        GUIDs of the two elements, used during deserialization when the live elements aren't available yet.
    **kwargs : dict, optional
        Any additional attributes are set directly on the instance and survive serialization.

    Attributes
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    elements : tuple(:class:`~compas_model.elements.Element`)
        The elements joined by this candidate.
    interactions : list(tuple(:class:`~compas_model.elements.Element`, :class:`~compas_model.elements.Element`))
        The element pairs this candidate connects.
    topology_info : :class:`~compas_timber.connections.TopologyInfo` | None
        The topology info of the connection. Values not given at construction are filled in by the
        connection solver on first access. ``None`` if nothing was given and it cannot be solved
        (unsupported element types, or elements not yet restored after deserialization).
    topology : literal, one of :class:`JointTopology` | None
        The topology by which the two elements interact.
    location : :class:`~compas.geometry.Point`
        The location of the interaction point of the two elements.
    distance : float | None
        Distance between the elements.

    """

    # keys of the pre-`topology_info` plate candidate data, now derived per element from `topology_info`.
    _LEGACY_KWARGS = ("a_segment_index", "b_segment_index")

    def __init__(
        self,
        element_a=None,
        element_b=None,
        topology_info=None,
        topology=None,
        location=None,
        distance=None,
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

        if topology_info is None and not (topology is None and location is None and distance is None):
            topology_info = TopologyInfo(topology, distance=distance, location=location)
        self._topology_info = topology_info
        self._solve_attempted = False  # avoids re-running the solver on every access when it can't fill the gaps

        for key in self._LEGACY_KWARGS:
            kwargs.pop(key, None)
        self._extra_kwargs = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def __data__(self):
        data = {
            "name": self.name,
            "element_guids": self.element_guids,
            "topology_info": self._topology_info,
        }
        data.update(self._extra_kwargs)
        return data

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
    def topology_info(self):
        if not self._solve_attempted and (self._topology_info is None or self._topology_info.location is None):
            self._complete_topology_info()
        return self._topology_info

    @property
    def topology(self):
        info = self.topology_info
        return info.topology if info else None

    @topology.setter
    def topology(self, value):
        self._ensure_topology_info().topology = value

    @property
    def distance(self):
        info = self.topology_info
        return info.distance if info else None

    @distance.setter
    def distance(self, value):
        self._ensure_topology_info().distance = value

    @property
    def location(self):
        info = self.topology_info
        location = info.location if info else None
        if location is None:
            raise ValueError("Location of the joint could not be determined. Please set it manually.")
        return location

    @location.setter
    def location(self, value):
        """Set the location of the joint."""
        if not isinstance(value, Point):
            raise TypeError("Location must be a Point.")
        self._ensure_topology_info().location = value

    def info_for(self, element):
        """Returns the per-element topology info (`BeamTopologyInfo`/`PlateTopologyInfo`) of `element`, or ``None`` if absent.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            One of the elements of this candidate.

        """
        info = self.topology_info
        return info.info_for(element) if info else None

    def reset_location(self):
        """Recompute the location of the connection from the elements' current geometry.

        If the per-element topology info is known, the registered connection solver updates the location in place
        (without searching for the topology again). Otherwise the location is cleared and re-solved on next access.

        """
        if self._topology_info is None:
            return
        if self._has_live_elements() and self._topology_info.element_topo_info and self._update_location_from_solver():
            return
        self._topology_info.location = None
        self._solve_attempted = False

    def _has_live_elements(self):
        return len(self._elements) == 2 and all(self._elements)

    def _ensure_topology_info(self):
        if self._topology_info is None:
            self._topology_info = TopologyInfo(None)
        return self._topology_info

    def _complete_topology_info(self):
        # Fills whatever is missing (the whole info, or only the parts the caller did not give) from the connection
        # solver registered for the elements' types. Values given by the caller are kept.
        if not self._has_live_elements():
            return  # e.g. not yet restored after deserialization, try again later
        self._solve_attempted = True
        from .candidate_dispatch import solve_topology  # avoid circular import

        solved = solve_topology(self.element_a, self.element_b)
        if solved is None:
            return
        if self._topology_info is None:
            self._topology_info = solved
            return
        info = self._topology_info
        if info.topology is None:
            info.topology = solved.topology
        if info.distance is None:
            info.distance = solved.distance
        if info.location is None:
            info.location = solved.location
        if not info.element_topo_info:
            info.element_topo_info = solved.element_topo_info
        if info.location is None and info.element_topo_info:
            # The caller gave a topology for elements the solver does not consider connected (e.g. beams further
            # apart than its tolerance). Their location is still well-defined geometrically.
            self._update_location_from_solver()

    def _update_location_from_solver(self):
        from .candidate_dispatch import find_connection_solver  # avoid circular import

        solver = find_connection_solver(self.element_a, self.element_b)
        if solver is None:
            return False
        try:
            solver.update_location(self.element_a, self.element_b, self._topology_info)
        except ValueError:
            return False
        return self._topology_info.location is not None

    def restore_elements_from_keys(self, model):
        """Restores the reference to the elements associated with this candidate.

        This method is called by :class:`compas_timber.model.TimberModel` during de-serialization to restore the
        references.

        """
        self._elements = tuple(model[guid] for guid in self.element_guids)

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of this candidate and creates the new connection in `model`.

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
