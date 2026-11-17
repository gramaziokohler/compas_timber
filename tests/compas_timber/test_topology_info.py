import pytest
from compas.geometry import Point

from compas_timber.connections import BeamTopologyInfo
from compas_timber.connections import JointTopology
from compas_timber.connections import TopologyInfo
from compas_timber.elements import Beam


@pytest.fixture
def beams():
    beam_a = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), width=0.1, height=0.1)
    beam_b = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), width=0.1, height=0.1)
    return beam_a, beam_b


def _topo_info(topology, entries):
    """Builds a `TopologyInfo` with `entries` (a list of `(element, role)`) inserted in the given order."""
    return TopologyInfo(topology, element_topo_info={str(element.guid): BeamTopologyInfo(role=role) for element, role in entries})


@pytest.mark.parametrize("insert_b_first", [False, True])
def test_reorder_elements_puts_main_first(beams, insert_b_first):
    beam_a, beam_b = beams
    entries = [(beam_a, "cross"), (beam_b, "main")]
    topo_info = _topo_info(JointTopology.TOPO_T, entries[::-1] if insert_b_first else entries)

    main, cross = topo_info.reorder_elements(beam_a, beam_b)

    assert main is beam_b and cross is beam_a


@pytest.mark.parametrize("insert_b_first", [False, True])
def test_reorder_elements_keeps_given_order_on_tie(beams, insert_b_first):
    beam_a, beam_b = beams
    entries = [(beam_a, "main"), (beam_b, "main")]
    topo_info = _topo_info(JointTopology.TOPO_L, entries[::-1] if insert_b_first else entries)

    assert topo_info.reorder_elements(beam_a, beam_b) == (beam_a, beam_b)
    assert topo_info.reorder_elements(beam_b, beam_a) == (beam_b, beam_a)


def test_reorder_elements_raises_for_missing_element(beams):
    beam_a, beam_b = beams
    topo_info = _topo_info(JointTopology.TOPO_T, [(beam_a, "main")])

    with pytest.raises(ValueError):
        topo_info.reorder_elements(beam_a, beam_b)
