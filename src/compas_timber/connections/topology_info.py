from compas.data import Data

# Canonical element ordering convention: the "main"/"edge" role always sorts before "cross"/"face".
# Used by `TopologyInfo.reorder_elements()` to derive a/b-style ordering without storing it positionally.
_ROLE_PRIORITY = {"main": 0, "edge": 0, "cross": 1, "face": 1}


def _role_priority(element_info):
    """Sort priority of an element's role; unset or unknown roles sort last."""
    return _ROLE_PRIORITY.get(element_info.role, 2)


class BeamTopologyInfo(Data):
    """Per-beam topology info describing how a single beam participates in a connection.

    Holds no reference to the beam itself — it is meant to be stored in `TopologyInfo.element_topo_info`,
    keyed by the beam's guid, which is how it gets correlated back to a live element.

    Parameters
    ----------
    role : literal("main", "cross"), optional
        ``"main"`` if this beam meets the other beam at one of its own ends, ``"cross"`` if it
        meets it along its length (mid-span). ``None`` when the topology is unknown.
    end : literal("start", "end"), optional
        Which end of this beam is involved in the connection. ``None`` when `role` is ``"cross"``.
    ref_side_index : int, optional
        Index of this beam's reference side that faces the other beam. ``None`` when not
        applicable (e.g. parallel beams, unknown topology).
    location_parameter : float, optional
        Absolute distance, in model units, from `beam.centerline.start` to the contact point along
        the centerline. ``None`` when not applicable.

    Attributes
    ----------
    role : literal("main", "cross") or None
    end : literal("start", "end") or None
    ref_side_index : int or None
    location_parameter : float or None

    """

    def __init__(self, role=None, end=None, ref_side_index=None, location_parameter=None):
        super(BeamTopologyInfo, self).__init__()
        self.role = role
        self.end = end
        self.ref_side_index = ref_side_index
        self.location_parameter = location_parameter

    @property
    def __data__(self):
        return {
            "role": self.role,
            "end": self.end,
            "ref_side_index": self.ref_side_index,
            "location_parameter": self.location_parameter,
        }

    def __repr__(self):
        return "BeamTopologyInfo(role={}, end={}, ref_side_index={}, location_parameter={})".format(self.role, self.end, self.ref_side_index, self.location_parameter)


class PlateTopologyInfo(Data):
    """Per-plate topology info describing how a single plate participates in a connection.

    Holds no reference to the plate itself — it is meant to be stored in `TopologyInfo.element_topo_info`,
    keyed by the plate's guid, which is how it gets correlated back to a live element.

    Parameters
    ----------
    role : literal("edge", "face"), optional
        ``"edge"`` if this plate's edge participates in the connection, ``"face"`` if this plate is
        the face-only side of a `TOPO_EDGE_FACE` connection. ``None`` when the topology is unknown.
    edge_index : int, optional
        The index of the segment in this plate's outline where the connection occurs. ``None`` when
        `role` is ``"face"`` or the topology is unknown.
    ref_side_index : int, optional
        Index of this plate's reference side, i.e. of the outline in `plate.outlines` (and the plane in
        `plate.planes`) on which the connection was detected. ``None`` when the topology is unknown.
        Together with `edge_index` it identifies the exact outline segment involved in the connection.
    location : :class:`~compas.geometry.Point`, optional
        The point on this plate closest to the joint.

    Attributes
    ----------
    role : literal("edge", "face") or None
    edge_index : int or None
    ref_side_index : int or None
    location : :class:`~compas.geometry.Point`

    """

    def __init__(self, role=None, edge_index=None, ref_side_index=None, location=None):
        super(PlateTopologyInfo, self).__init__()
        self.role = role
        self.edge_index = edge_index
        self.ref_side_index = ref_side_index
        self.location = location

    @property
    def __data__(self):
        return {"role": self.role, "edge_index": self.edge_index, "ref_side_index": self.ref_side_index, "location": self.location}

    def __repr__(self):
        return "PlateTopologyInfo(role={}, edge_index={}, ref_side_index={}, location={})".format(self.role, self.edge_index, self.ref_side_index, self.location)


class TopologyInfo(Data):
    """Data structure to hold the results of a connection topology analysis between two (or more) elements.

    Per-element info (`BeamTopologyInfo`/`PlateTopologyInfo`) holds no reference to its element — it
    is correlated to a live element via `element_topo_info`, a dict keyed by `str(element.guid)`.
    This lets `TopologyInfo` represent any pair (or, in principle, group) of element types uniformly,
    including a mix of types (e.g. a beam-to-plate connection), without needing to resolve or store
    live elements itself.

    Parameters
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    distance : float, optional
        The distance between the closest points of the elements.
    location : :class:`~compas.geometry.Point`, optional
        The location of the intersection.
    element_topo_info : dict(str, :class:`~compas_timber.connections.BeamTopologyInfo` or :class:`~compas_timber.connections.PlateTopologyInfo`), optional
        Per-element topology info, keyed by `str(element.guid)`.

    Attributes
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    distance : float or None
        The distance between the closest points of the elements.
    location : :class:`~compas.geometry.Point` or None
        The location of the intersection.
    element_topo_info : dict(str, :class:`~compas_timber.connections.BeamTopologyInfo` or :class:`~compas_timber.connections.PlateTopologyInfo`)
        Per-element topology info, keyed by `str(element.guid)`.

    """

    def __init__(self, topology, distance=None, location=None, element_topo_info=None):
        super(TopologyInfo, self).__init__()
        self.topology = topology
        self.distance = distance
        self.location = location
        self.element_topo_info = element_topo_info or {}

    @property
    def __data__(self):
        return {
            "topology": self.topology,
            "distance": self.distance,
            "location": self.location,
            "element_topo_info": self.element_topo_info,
        }

    def __repr__(self):
        return "TopologyInfo(topology={}, distance={}, location={}, element_topo_info={})".format(self.topology, self.distance, self.location, self.element_topo_info)

    def info_for(self, element):
        """Returns the `BeamTopologyInfo`/`PlateTopologyInfo` entry for a live `element`, or ``None`` if absent.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The live element to look up.

        Returns
        -------
        :class:`~compas_timber.connections.BeamTopologyInfo` or :class:`~compas_timber.connections.PlateTopologyInfo` or None

        """
        return self.element_topo_info.get(str(element.guid))

    def reorder_elements(self, element_a, element_b):
        """Returns `element_a` and `element_b` in the role order determined by the solver (main/edge first, cross/face second).

        The pair is swapped only if `element_b` holds the leading role and `element_a` does not; ties
        (e.g. `TOPO_L`, `TOPO_X`, `TOPO_EDGE_EDGE` or unset roles) keep the given order.

        Parameters
        ----------
        element_a : :class:`~compas_model.elements.Element`
            First element of the pair.
        element_b : :class:`~compas_model.elements.Element`
            Second element of the pair.

        Returns
        -------
        tuple(:class:`~compas_model.elements.Element`, :class:`~compas_model.elements.Element`)

        Raises
        ------
        ValueError
            If either element has no entry in `element_topo_info`.

        """
        info_a = self.info_for(element_a)
        info_b = self.info_for(element_b)
        if info_a is None or info_b is None:
            raise ValueError("Both elements must be present in this topology's `element_topo_info`.")
        if _role_priority(info_b) < _role_priority(info_a):
            return element_b, element_a
        return element_a, element_b
