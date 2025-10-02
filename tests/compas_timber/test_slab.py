from math import e
import pytest

from compas.geometry import Point, Polyline, Vector, Frame, Transformation
from compas.tolerance import TOL


from compas_timber.elements import Slab, beam
from compas_timber.elements import Opening
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel

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
        slab.add_element(element)
    assert TOL.is_allclose(beams[0].frame.point, Point(100, 500, 0))
    assert TOL.is_allclose(beams[1].frame.point, Point(100, 4500, 0))
    assert TOL.is_allclose(plate.frame.point, Point(200, 0, 0))
    assert TOL.is_allclose(opening.frame.point, Point(0, 2000, 500))
    assert TOL.is_allclose(beams[0].frame.xaxis, Vector(0, 0, 1))
    assert TOL.is_allclose(beams[1].frame.xaxis, Vector(0, 0, 1))
    assert TOL.is_allclose(plate.frame.xaxis, Vector(0, 1, 0))
    assert all(e in slab.elements for e in beams + [opening] + [plate])

def test_add_container_element(slab, beams, opening, plate):
    model = TimberModel()
    model.add_container_element(slab)
    assert all(e in list(model.elements()) for e in beams + [opening] + [plate])


def test_slab_add_elements(slab, beams, opening, plate):
    for element in beams + [opening] + [plate]:
        slab.add_element(element)
    model = TimberModel()
    model.add_container_element(slab)
    assert TOL.is_allclose(beams[0].frame.point, Point(100, 500, 0))
    assert TOL.is_allclose(beams[1].frame.point, Point(100, 4500, 0))
    assert TOL.is_allclose(plate.frame.point, Point(200, 0, 0))
    assert TOL.is_allclose(opening.frame.point, Point(0, 2000, 500))
    assert TOL.is_allclose(beams[0].frame.xaxis, Vector(0, 0, 1))
    assert TOL.is_allclose(beams[1].frame.xaxis, Vector(0, 0, 1))
    assert TOL.is_allclose(plate.frame.xaxis, Vector(0, 1, 0))
    assert TOL.is_allclose(Frame.from_transformation(beams[0].transformation).point, Point(500, 0, 100))
    assert TOL.is_allclose(Frame.from_transformation(beams[1].transformation).point, Point(4500, 0, 100))
    assert TOL.is_allclose(Frame.from_transformation(plate.transformation).point, Point(0, 0, 200))
    assert TOL.is_allclose(Frame.from_transformation(opening.transformation).point, Point(2000, 500, 0))
    assert all(e in slab.elements for e in beams + [opening] + [plate])



def test_move_container_element(slab, beams, opening, plate):
    model = TimberModel()
    # for element in beams + [opening] + [plate]:
    #     element.transform(slab.transformation_to_local())
    #     slab.add_element(element)
    model.add_container_element(slab)
    frame_a = Frame.worldXY()
    frame_b = Frame.worldXY()
    frame_b.point = Point(1000, 0, 0)
    # slab.transform(Transformation.from_frame_to_frame(frame_a, frame_b))
    assert TOL.is_allclose(beams[0].frame.point, Point(500, 0, 100))
    assert TOL.is_allclose(beams[1].frame.point, Point(4500, 0, 100))
    assert TOL.is_allclose(plate.frame.point, Point(0, 0, 200))
    assert TOL.is_allclose(opening.frame.point, Point(2000, 500, 0))
    assert TOL.is_allclose(beams[0].frame.transformed(beams[0].compute_modeltransformation()).point, Point(100, 500, 0))
    assert TOL.is_allclose(beams[1].frame.transformed(beams[1].compute_modeltransformation()).point, Point(1100, 4500, 0))
    assert TOL.is_allclose(plate.frame.transformed(plate.compute_modeltransformation()).point, Point(200, 0, 0))
    assert TOL.is_allclose(opening.frame.transformed(opening.compute_modeltransformation()).point, Point(2000, 500, 0))


def test_add_elements_to_container_element(slab, beams, opening, plate):
    model = TimberModel()
    model.add_container_element(slab)
    for element in beams + [opening] + [plate]:
        element.transform(slab.transformation_to_local())
        slab.add_element(element)
    assert all(e in list(model.elements()) for e in beams + [opening] + [plate])
    assert all(e.parent == slab for e in beams + [opening] + [plate])
    assert all(e in slab.children for e in beams + [opening] + [plate])

def test_add_elements_to_container_removes_from_old_model(slab, beams, opening, plate):
    old_model = TimberModel()
    for element in beams + [opening] + [plate]:
        old_model.add_element(element)
    model = TimberModel()
    model.add_container_element(slab)
    for element in beams + [opening] + [plate]:
        element.transform(slab.transformation_to_local())
        slab.add_element(element)
    assert all(e in list(model.elements()) for e in beams + [opening] + [plate])
    assert all(e not in list(old_model.elements()) for e in beams + [opening] + [plate])
