import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector

from compas_timber.connections import BeamTopologyInfo
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import PlateTopologyInfo
from compas_timber.connections import TopologyInfo
from compas_timber.elements import Beam
from compas_timber.elements import Plate


@pytest.fixture
def beams():
    beam_a = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), width=0.1, height=0.1)
    beam_b = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), width=0.1, height=0.1)
    return beam_a, beam_b


def _topo_info(topology, entries):
    """Builds a `TopologyInfo` with `entries` (a list of `(element, role)`) inserted in the given order."""
    return TopologyInfo(topology, element_topo_info={str(element.guid): BeamTopologyInfo(role=role) for element, role in entries})


@pytest.mark.parametrize("insert_b_first", [False, True])
def test_get_element_by_role_puts_main_first(beams, insert_b_first):
    beam_a, beam_b = beams
    entries = [(beam_a, "cross"), (beam_b, "main")]
    topo_info = _topo_info(JointTopology.TOPO_T, entries[::-1] if insert_b_first else entries)

    main, cross = topo_info.get_element_by_role(beam_a, beam_b)

    assert main is beam_b and cross is beam_a


@pytest.mark.parametrize("insert_b_first", [False, True])
def test_get_element_by_role_keeps_given_order_on_tie(beams, insert_b_first):
    beam_a, beam_b = beams
    entries = [(beam_a, "main"), (beam_b, "main")]
    topo_info = _topo_info(JointTopology.TOPO_L, entries[::-1] if insert_b_first else entries)

    assert topo_info.get_element_by_role(beam_a, beam_b) == (beam_a, beam_b)
    assert topo_info.get_element_by_role(beam_b, beam_a) == (beam_b, beam_a)


def test_get_element_by_role_raises_for_missing_element(beams):
    beam_a, beam_b = beams
    topo_info = _topo_info(JointTopology.TOPO_T, [(beam_a, "main")])

    with pytest.raises(ValueError):
        topo_info.get_element_by_role(beam_a, beam_b)


def _json_roundtrip(topo_info):
    """Round-trips `topo_info` through compas JSON and checks the parts every case shares."""
    other = json_loads(json_dumps(topo_info))
    assert type(other) is TopologyInfo
    assert str(other.guid) == str(topo_info.guid)
    assert other.topology == topo_info.topology
    assert other.distance == topo_info.distance
    assert other.location == topo_info.location
    assert set(other.element_topo_info) == set(topo_info.element_topo_info)
    for guid, info in topo_info.element_topo_info.items():
        assert type(other.element_topo_info[guid]) is type(info)
        assert other.element_topo_info[guid].__data__ == info.__data__
    return other


def test_beam_topology_info_json_roundtrip(beams):
    beam_a, beam_b = beams
    topo_info = ConnectionSolver().find_topology(beam_a, beam_b)
    assert topo_info.topology == JointTopology.TOPO_L

    other = _json_roundtrip(topo_info)

    assert other.get_element_by_role(beam_a, beam_b) == (beam_a, beam_b)
    assert isinstance(other.info_for(beam_a), BeamTopologyInfo)
    assert other.info_for(beam_a).end == "start"


def test_plate_topology_info_json_roundtrip():
    face = Plate.from_outline_thickness(Polyline([[0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0], [0, 0, 0]]), 10)
    edge = Plate.from_outline_thickness(Polyline([[50, -50, 0], [50, 50, 0], [50, 50, 100], [50, -50, 100], [50, -50, 0]]), 10, vector=Vector(1, 0, 0))
    topo_info = PlateConnectionSolver().find_topology(face, edge, max_distance=1.0)
    assert topo_info.topology == JointTopology.TOPO_EDGE_FACE

    other = _json_roundtrip(topo_info)

    assert other.get_element_by_role(face, edge) == (edge, face)
    assert isinstance(other.info_for(edge), PlateTopologyInfo)
    assert isinstance(other.info_for(edge).location, Point)
    assert other.info_for(face).edge_index is None


def test_unknown_topology_info_json_roundtrip():
    """Unset fields stay ``None`` after a round-trip."""
    topo_info = TopologyInfo(JointTopology.TOPO_UNKNOWN, element_topo_info={"aaa": PlateTopologyInfo(), "bbb": PlateTopologyInfo()})

    other = _json_roundtrip(topo_info)

    assert other.distance is None and other.location is None
    assert all(v is None for v in other.element_topo_info["aaa"].__data__.values())


@pytest.mark.parametrize(
    "obj,expected",
    [
        (BeamTopologyInfo(role="main", end="start", ref_side_index=1, location_parameter=2.5), "BeamTopologyInfo(role=main, end=start, ref_side_index=1, location_parameter=2.5)"),
        (PlateTopologyInfo(role="face", ref_side_index=0), "PlateTopologyInfo(role=face, edge_index=None, ref_side_index=0, location=None)"),
        (TopologyInfo(JointTopology.TOPO_UNKNOWN), "TopologyInfo(topology=0, distance=None, location=None, element_topo_info={})"),
    ],
)
def test_repr(obj, expected):
    assert repr(obj) == expected
