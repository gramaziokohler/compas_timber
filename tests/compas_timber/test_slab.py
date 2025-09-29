import pytest

from compas.geometry import Point, Polyline, Vector, Frame


from compas_timber.elements import Slab
from compas_timber.elements import Opening
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def slab():
    """Create a basic TimberModel with two plates."""
    # Create two plates
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 5000, 0), Point(0, 5000, 3000), Point(0, 0, 3000), Point(0, 0, 0)])
    polyline_b = Polyline([Point(200, 0, 0), Point(200, 5000, 0), Point(200, 5000, 3000), Point(200, 0, 3000), Point(200, 0, 0)])
    return Slab(polyline_a, polyline_b)

@pytest.fixture
def beams():
    """Create a basic TimberModel with two plates."""
    beam_a = Beam(Frame(Point(100, 500, 0)),3000,50,200)
    beam_b = Beam(Frame(Point(100, 4500, 0)),3000,50,200)
    return [beam_a, beam_b]

@pytest.fixture
def opening():
    """Create a basic TimberModel with two plates."""
    opening_outline = Polyline([Point(0, 2000, 500), Point(0, 3000, 500), Point(0, 3000, 2500), Point(0, 2000, 2500), Point(0, 2000, 500)])
    return Opening(opening_outline)

def test_slab_add_elements(slab, beams, opening):
    for element in beams + [opening]:
        element.transform(slab.transformation_to_local())
        slab.add_element(element)
    assert(beams[0].frame.point == Point(500,0,0))
    # assert(beams[1].frame.point == Point(4500,0,0))
    # assert(opening.frame.point == Point(2000,500,0))
    # assert(beams[0].frame.xaxis == Vector(0,1,0))
    # assert(beams[1].frame.xaxis == Vector(0,1,0))
