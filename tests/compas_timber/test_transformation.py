import pytest

from compas.geometry import Point, Frame
from compas.tolerance import TOL

from compas_timber.elements import Plate, Beam
from compas_timber.model import TimberModel


def test_flat_plate_creation():
    plate = Plate(Frame(Point(10,0,0), [1,0,0], [0,1,0]), 10, 20, 1)
    beam = Beam(Frame(Point(0,10,0), [0,0,1], [1,0,0]), 10, 1, 1)
    box = beam.blank.copy()
    box.transform(plate.transformation)
    model = TimberModel()
    model.add_element(plate)
    model.add_element(beam, parent=plate)
    beam.add_blank_extension(0,0)

    assert all([e in model.elements() for e in [plate, beam]]), "Expected plate and beam to be in model"
    assert beam in plate.children, "Expected beam to be child of plate"
    assert plate is beam.parent, "Expected plate to be parent of beam"
    assert beam.modeltransformation == plate.transformation * beam.transformation, "Expected beam transformation to be combination of plate and beam transformations"
    assert all([TOL.is_allclose(a, b) for a, b in zip(beam.blank.points, box.points)]), "Expected beam blank to be correctly transformed"
# ======================================================================
