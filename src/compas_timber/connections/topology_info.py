from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import Optional
from typing import Union

from compas.data import Data

if TYPE_CHECKING:
    from compas.geometry import Point
    from compas_model.elements import Element

BeamRole = Literal["main", "cross"]
BeamEnd = Literal["start", "end"]
PlateRole = Literal["edge", "face"]

# Canonical element ordering convention: the "main"/"edge" role always sorts before "cross"/"face".
# Used by `TopologyInfo.reorder_elements()` to derive a/b-style ordering without storing it positionally.
_ROLE_PRIORITY = {"main": 0, "edge": 0, "cross": 1, "face": 1}


def _role_priority(element_info: ElementTopologyInfo) -> int:
    """Sort priority of an element's role; unset or unknown roles sort last."""
    return _ROLE_PRIORITY.get(element_info.role, 2)


class BeamTopologyInfo(Data):
    """Per-beam topology info describing how a single beam participates in a connection.

    Holds no reference to the beam itself — it is meant to be stored in `TopologyInfo.element_topo_info`,
    keyed by the beam's guid, which is how it gets correlated back to a live element.

    Parameters
    ----------
    role
        ``"main"`` if this beam meets the other beam at one of its own ends, ``"cross"`` if it
        meets it along its length (mid-span). ``None`` when the topology is unknown.
    end
        Which end of this beam is involved in the connection. ``None`` when `role` is ``"cross"``.
    ref_side_index
        Index of this beam's reference side that faces the other beam. ``None`` when not
        applicable (e.g. parallel beams, unknown topology).
    location_parameter
        Absolute distance, in model units, from `beam.centerline.start` to the contact point along
        the centerline. ``None`` when not applicable.

    """

    def __init__(
        self,
        role: Optional[BeamRole] = None,
        end: Optional[BeamEnd] = None,
        ref_side_index: Optional[int] = None,
        location_parameter: Optional[float] = None,
    ) -> None:
        super(BeamTopologyInfo, self).__init__()
        self.role = role
        self.end = end
        self.ref_side_index = ref_side_index
        self.location_parameter = location_parameter

    @property
    def __data__(self) -> dict:
        return {
            "role": self.role,
            "end": self.end,
            "ref_side_index": self.ref_side_index,
            "location_parameter": self.location_parameter,
        }

    def __repr__(self) -> str:
        return "BeamTopologyInfo(role={}, end={}, ref_side_index={}, location_parameter={})".format(self.role, self.end, self.ref_side_index, self.location_parameter)


class PlateTopologyInfo(Data):
    """Per-plate topology info describing how a single plate participates in a connection.

    Holds no reference to the plate itself — it is meant to be stored in `TopologyInfo.element_topo_info`,
    keyed by the plate's guid, which is how it gets correlated back to a live element.

    Parameters
    ----------
    role
        ``"edge"`` if this plate's edge participates in the connection, ``"face"`` if this plate is
        the face-only side of a `TOPO_EDGE_FACE` connection. ``None`` when the topology is unknown.
    edge_index
        The index of the segment in this plate's outline where the connection occurs. ``None`` when
        `role` is ``"face"`` or the topology is unknown.
    ref_side_index
        Index of this plate's reference side, i.e. of the outline in `plate.outlines` (and the plane in
        `plate.planes`) on which the connection was detected. ``None`` when the topology is unknown.
        Together with `edge_index` it identifies the exact outline segment involved in the connection.
    location
        The point on this plate closest to the joint. ``None`` when the topology is unknown.

    """

    def __init__(
        self,
        role: Optional[PlateRole] = None,
        edge_index: Optional[int] = None,
        ref_side_index: Optional[int] = None,
        location: Optional[Point] = None,
    ) -> None:
        super(PlateTopologyInfo, self).__init__()
        self.role = role
        self.edge_index = edge_index
        self.ref_side_index = ref_side_index
        self.location = location

    @property
    def __data__(self) -> dict:
        return {"role": self.role, "edge_index": self.edge_index, "ref_side_index": self.ref_side_index, "location": self.location}

    def __repr__(self) -> str:
        return "PlateTopologyInfo(role={}, edge_index={}, ref_side_index={}, location={})".format(self.role, self.edge_index, self.ref_side_index, self.location)


ElementTopologyInfo = Union[BeamTopologyInfo, PlateTopologyInfo]


class TopologyInfo(Data):
    """Data structure to hold the results of a connection topology analysis between two (or more) elements.

    Per-element info (`BeamTopologyInfo`/`PlateTopologyInfo`) holds no reference to its element — it
    is correlated to a live element via `element_topo_info`, a dict keyed by `str(element.guid)`.
    This lets `TopologyInfo` represent any pair (or, in principle, group) of element types uniformly,
    including a mix of types (e.g. a beam-to-plate connection), without needing to resolve or store
    live elements itself.

    Parameters
    ----------
    topology
        The topology of the intersection, one of the :class:`~compas_timber.connections.JointTopology` constants.
    distance
        The distance between the closest points of the elements. ``None`` when the topology is unknown.
    location
        The location of the intersection. ``None`` when the topology is unknown.
    element_topo_info
        Per-element topology info, keyed by `str(element.guid)`. Defaults to an empty dict.

    """

    def __init__(
        self,
        topology: int,
        distance: Optional[float] = None,
        location: Optional[Point] = None,
        element_topo_info: Optional[dict[str, ElementTopologyInfo]] = None,
    ) -> None:
        super(TopologyInfo, self).__init__()
        self.topology = topology
        self.distance = distance
        self.location = location
        self.element_topo_info: dict[str, ElementTopologyInfo] = element_topo_info or {}

    @property
    def __data__(self) -> dict:
        return {
            "topology": self.topology,
            "distance": self.distance,
            "location": self.location,
            "element_topo_info": self.element_topo_info,
        }

    def __repr__(self) -> str:
        return "TopologyInfo(topology={}, distance={}, location={}, element_topo_info={})".format(self.topology, self.distance, self.location, self.element_topo_info)

    def info_for(self, element: Element) -> Optional[ElementTopologyInfo]:
        """Returns the `BeamTopologyInfo`/`PlateTopologyInfo` entry for a live `element`, or ``None`` if absent.

        Parameters
        ----------
        element
            The live element to look up.

        """
        return self.element_topo_info.get(str(element.guid))

    def reorder_elements(self, element_a: Element, element_b: Element) -> tuple[Element, Element]:
        """Returns `element_a` and `element_b` in the role order determined by the solver (main/edge first, cross/face second).

        The pair is swapped only if `element_b` holds the leading role and `element_a` does not; ties
        (e.g. `TOPO_L`, `TOPO_X`, `TOPO_EDGE_EDGE` or unset roles) keep the given order.

        Parameters
        ----------
        element_a
            First element of the pair.
        element_b
            Second element of the pair.

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
