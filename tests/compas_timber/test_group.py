import pytest

from compas.geometry import Polyline
from compas.geometry import Point
from compas.geometry import Vector
from compas_timber.elements import Slab
from compas_timber.elements import Beam
from compas_timber.model import TimberModel

@pytest.fixture
def model():
    return TimberModel()

@pytest.fixture
def beam():
    return Beam.from_endpoints(Point(15,10,0), Point(15,20,0), 1,2)

@pytest.fixture
def slab():
    return Slab.from_outline_thickness(Polyline([Point(10,10,0),Point(20,10,0),Point(20,20,0),Point(10,20,0),Point(10,10,0)]), 1, vector=Vector.Zaxis(), name="test_slab")


def test_add_element_to_slab(slab, beam, model):
    centerline = beam.centerline.copy()

    slab.add_element(beam)

    assert beam.frame.point == Point(5,0,0)
    assert len(list(model.elements())) == 0
    model.add_element(slab)
    assert len(list(model.elements())) == 2
    assert beam.centerline == centerline
