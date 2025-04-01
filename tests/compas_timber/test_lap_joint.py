import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Point
from compas.geometry import Line

from compas_timber.elements import Beam
from compas_timber.connections import LLapJoint
from compas_timber.model import TimberModel


@pytest.fixture
def beam_a():
    line = Line(Point(x=4.29781540252867, y=35.42482180056156, z=0.0), Point(x=194.13139833231588, y=90.20267160119664, z=0.0))
    return Beam.from_centerline(line, width=10.0, height=20.0)


@pytest.fixture
def beam_b():
    line = Line(Point(x=4.29781540252867, y=35.42482180056156, z=0.0), Point(x=11.853380892271431, y=-121.35316211160092, z=0.0))
    return Beam.from_centerline(line, width=10.0, height=20.0)


def test_create_lap(beam_a, beam_b):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    joint = LLapJoint.create(model, beam_a, beam_b, lap_length=100.0, lap_depth=20.0, cut_plane_bias=0.5)

    assert len(model.joints) == 1
    assert isinstance(joint, LLapJoint)


def test_create_lap_serialize(beam_a, beam_b):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    joint = LLapJoint.create(model, beam_a, beam_b, lap_length=100.0, lap_depth=20.0, cut_plane_bias=0.5)

    model = json_loads(json_dumps(model))

    assert len(model.joints) == 1
    assert isinstance(joint, LLapJoint)

    deserialized_joint = list(model.joints)[0]
    assert isinstance(deserialized_joint, LLapJoint)
    assert deserialized_joint.main_beam is not None
    assert deserialized_joint.cross_beam is not None
