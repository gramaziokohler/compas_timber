import pytest

from compas.geometry import Point
from compas.geometry import Line


from compas_timber.elements import Beam
from compas_timber.connections.k_miter import KMiterJoint
from compas_timber.model import TimberModel


@pytest.fixture
def cross_beam():
    line = Line(Point(0.0, 0.0, 0.0), Point(500, 0, 0))
    return Beam.from_centerline(line, width=20.0, height=30.0)


@pytest.fixture
def beam_a():
    line = Line(Point(250, 0.0, 0.0), Point(150, 0, 200))
    return Beam.from_centerline(line, width=20.0, height=30.0)


@pytest.fixture
def beam_b():
    line = Line(Point(270, 0.0, 0.0), Point(350, 0.0, 200))
    return Beam.from_centerline(line, width=20.0, height=30.0)


def test_create_k_butt(beam_a, beam_b, cross_beam):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)
    model.add_element(cross_beam)
    joint = KMiterJoint.create(model, cross_beam, beam_a, beam_b, mill_depth=15.0)
    assert len(model.joints) == 1
    assert isinstance(joint, KMiterJoint)


def test_model_process_joinery(beam_a, beam_b, cross_beam):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)
    model.add_element(cross_beam)
    joint = KMiterJoint(cross_beam, beam_a, beam_b, mill_depth=15.0)
    model.add_joint(joint)
    model.process_joinery()
    assert isinstance(joint, KMiterJoint)
    assert joint.mill_depth == 15.0
    assert len(model.joints) == 1
