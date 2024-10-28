import pytest
from compas_timber.elements.fasteners.fastener import Fastener
from compas_timber.elements import Beam
from compas.geometry import Frame


@pytest.fixture
def mock_elements():
    beam_1 = Beam(Frame([0.0,0.0,0.0], [1.0,0.0,0.0], [0.0,1.0,0.0]), 100.0, 10.0, 20.0)
    beam_2 = Beam(Frame([0.0,0.0,0.0], [0.0,1.0,0.0], [-1.0,0.0,0.0]), 100.0, 10.0, 20.0)
    return [beam_1, beam_2]

def test_fastener_initialization(mock_elements):
    fastener = Fastener(mock_elements)
    assert fastener.elements == mock_elements
    assert fastener.features == []
    assert fastener.attributes == {}
    assert fastener.debug_info == []

def test_fastener_repr(mock_elements):
    fastener = Fastener(mock_elements)
    assert repr(fastener) == "Fastener(Beam None, Beam None)"

def test_fastener_str(mock_elements):
    fastener = Fastener(mock_elements)
    assert str(fastener) == "Fastener connecting Beam None, Beam None"

def test_fastener_is_fastener(mock_elements):
    fastener = Fastener(mock_elements)
    assert fastener.is_fastener is True

def test_fastener_add_features(mock_elements):
    fastener = Fastener(mock_elements)
    feature = "feature1"
    fastener.add_features(feature)
    assert fastener.features == [feature]

def test_fastener_remove_features(mock_elements):
    fastener = Fastener(mock_elements)
    feature = "feature1"
    fastener.add_features(feature)
    fastener.remove_features(feature)
    assert fastener.features == []

def test_fastener_remove_all_features(mock_elements):
    fastener = Fastener(mock_elements)
    feature1 = "feature1"
    feature2 = "feature2"
    fastener.add_features([feature1, feature2])
    fastener.remove_features()
    assert fastener.features == []
