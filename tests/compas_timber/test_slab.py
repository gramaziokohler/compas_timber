import pytest

from compas.geometry import Point, Polyline, Vector, Frame
from compas.tolerance import TOL


from compas_timber.elements import Slab
from compas_timber.elements import Opening
from compas_timber.elements import Beam
from compas_timber.elements import Plate


@pytest.fixture
def slab():
    """Create a basic TimberModel with two plates."""
    # Create two plates
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 5000, 0), Point(0, 5000, 3000), Point(0, 0, 3000), Point(0, 0, 0)])
    polyline_b = Polyline([Point(200, 0, 0), Point(200, 5000, 0), Point(200, 5000, 3000), Point(200, 0, 3000), Point(200, 0, 0)])
    return Slab.from_outlines(polyline_a, polyline_b)


@pytest.fixture
def beams():
    """Create a basic TimberModel with two plates."""
    beam_a = Beam(Frame(Point(100, 500, 0), Vector(0, 0, 1), Vector(1, 0, 0)), 3000, 50, 200)
    beam_b = Beam(Frame(Point(100, 4500, 0), Vector(0, 0, 1), Vector(1, 0, 0)), 3000, 50, 200)
    return [beam_a, beam_b]


@pytest.fixture
def plate():
    """Create a basic TimberModel with two plates."""
    # Create two plates
    polyline_a = Polyline([Point(200, 0, 0), Point(200, 5000, 0), Point(200, 5000, 3000), Point(200, 0, 3000), Point(200, 0, 0)])
    polyline_b = Polyline([Point(250, 0, 0), Point(250, 5000, 0), Point(250, 5000, 3000), Point(250, 0, 3000), Point(250, 0, 0)])
    return Plate.from_outlines(polyline_a, polyline_b)


@pytest.fixture
def opening():
    """Create a basic TimberModel with two plates."""
    opening_outline = Polyline([Point(0, 2000, 500), Point(0, 3000, 500), Point(0, 3000, 2500), Point(0, 2000, 2500), Point(0, 2000, 500)])
    opening_frame = Frame(Point(0, 2000, 500), Vector(0, 1, 0), Vector(0, 0, 1))
    return Opening(opening_frame, opening_outline)


def test_slab_add_elements(slab, beams, opening, plate):
    for element in beams + [opening] + [plate]:
        element.transform(slab.transformation_to_local())
        slab.add_element(element)
    assert TOL.is_allclose(beams[0].frame.point, Point(500, 0, 100))
    assert TOL.is_allclose(beams[1].frame.point, Point(4500, 0, 100))
    assert TOL.is_allclose(plate.frame.point, Point(0, 0, 200))
    assert TOL.is_allclose(opening.frame.point, Point(2000, 500, 0))
    assert TOL.is_allclose(beams[0].frame.xaxis, Vector(0, 1, 0))
    assert TOL.is_allclose(beams[1].frame.xaxis, Vector(0, 1, 0))
    assert TOL.is_allclose(plate.frame.xaxis, Vector(1, 0, 0))
