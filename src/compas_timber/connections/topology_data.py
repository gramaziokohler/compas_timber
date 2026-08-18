from compas.data import Data
from compas_model.elements import Element

# Canonical element ordering convention: the "main"/"edge" role always sorts before "cross"/"face".
# Used by `TopologyData.ordered_guids()` to derive a/b-style ordering without storing it positionally.
_ROLE_PRIORITY = {"main": 0, "edge": 0, "cross": 1, "face": 1}


class BeamTopologyData(Data):
    """Per-beam topology data describing how a single beam participates in a connection.

    Holds no reference to the beam itself — it is meant to be stored in `TopologyData.element_topo_data`,
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
        super(BeamTopologyData, self).__init__()
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
        return "BeamTopologyData(role={}, end={}, ref_side_index={}, location_parameter={})".format(self.role, self.end, self.ref_side_index, self.location_parameter)


class PlateTopologyData(Data):
    """Per-plate topology data describing how a single plate participates in a connection.

    Holds no reference to the plate itself — it is meant to be stored in `TopologyData.element_topo_data`,
    keyed by the plate's guid, which is how it gets correlated back to a live element.

    Parameters
    ----------
    role : literal("edge", "face"), optional
        ``"edge"`` if this plate's edge participates in the connection, ``"face"`` if this plate is
        the face-only side of a `TOPO_EDGE_FACE` connection. ``None`` when the topology is unknown.
    edge_index : int, optional
        The index of the segment in this plate's outline where the connection occurs. ``None`` when
        `role` is ``"face"`` or the topology is unknown.
    location : :class:`~compas.geometry.Point`, optional
        The point on this plate closest to the joint.

    Attributes
    ----------
    role : literal("edge", "face") or None
    edge_index : int or None
    location : :class:`~compas.geometry.Point`

    """

    def __init__(self, role=None, edge_index=None, location=None):
        super(PlateTopologyData, self).__init__()
        self.role = role
        self.edge_index = edge_index
        self.location = location

    @property
    def __data__(self):
        return {"role": self.role, "edge_index": self.edge_index, "location": self.location}

    def __repr__(self):
        return "PlateTopologyData(role={}, edge_index={}, location={})".format(self.role, self.edge_index, self.location)


class TopologyData(Data):
    """Data structure to hold the results of a connection topology analysis between two (or more) elements.

    Per-element data (`BeamTopologyData`/`PlateTopologyData`) holds no reference to its element — it
    is correlated to a live element via `element_topo_data`, a dict keyed by `str(element.guid)`.
    This lets `TopologyData` represent any pair (or, in principle, group) of element types uniformly,
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
    element_topo_data : dict(str, :class:`~compas_timber.connections.BeamTopologyData` or :class:`~compas_timber.connections.PlateTopologyData`), optional
        Per-element topology data, keyed by `str(element.guid)`.

    Attributes
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    distance : float or None
        The distance between the closest points of the elements.
    location : :class:`~compas.geometry.Point` or None
        The location of the intersection.
    element_topo_data : dict(str, :class:`~compas_timber.connections.BeamTopologyData` or :class:`~compas_timber.connections.PlateTopologyData`)
        Per-element topology data, keyed by `str(element.guid)`.

    """

    def __init__(self, topology, distance=None, location=None, element_topo_data=None):
        super(TopologyData, self).__init__()
        self.topology = topology
        self.distance = distance
        self.location = location
        self.element_topo_data = element_topo_data or {}

    @property
    def __data__(self):
        return {
            "topology": self.topology,
            "distance": self.distance,
            "location": self.location,
            "element_topo_data": self.element_topo_data,
        }

    def __repr__(self):
        return "TopologyData(topology={}, distance={}, location={}, element_topo_data={})".format(self.topology, self.distance, self.location, self.element_topo_data)

    def data_for(self, element):
        """Returns the `BeamTopologyData`/`PlateTopologyData` entry for a live `element`, or ``None`` if absent.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The live element to look up.

        Returns
        -------
        :class:`~compas_timber.connections.BeamTopologyData` or :class:`~compas_timber.connections.PlateTopologyData` or None

        """
        return self.element_topo_data.get(str(element.guid))

    def ordered_guids(self):
        """Returns this topology's element guids in canonical role order (main/edge first, cross/face second).

        Ties (e.g. equal or unset roles) keep the original insertion order of `element_topo_data`.

        Returns
        -------
        list(str)

        """
        return sorted(self.element_topo_data, key=lambda guid: _ROLE_PRIORITY.get(self.element_topo_data[guid].role, 2))

    def reorder_elements(self, element_a: Element, element_b: Element) -> list[Element]:
        """Returns `element_a` and `element_b` in the role order determined by the solver (main/edge first, cross/face second)."""
        if not (set((str(element_a.guid), str(element_b.guid))) <= set(self.element_topo_data)):
            raise ValueError("Both elements must be present in this topology's `element_topo_data`.")
        elements_by_guid = {str(element_a.guid): element_a, str(element_b.guid): element_b}
        return [elements_by_guid[guid] for guid in self.ordered_guids()]
