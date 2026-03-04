import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame

from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.planning import SimpleSequenceGenerator


@pytest.fixture
def mock_model():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b3 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b4 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b5 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    for b in [b1, b2, b3, b4, b5]:
        model.add_element(b)
    return model


def test_simple_sequence_generator(mock_model):
    generator = SimpleSequenceGenerator(mock_model)
    plan = generator.result

    assert len(plan) == len(mock_model.beams)
    for step, beam in zip(plan, mock_model.beams):
        assert str(beam.guid) == step.element_ids[0]


def test_simple_sequence_generator_get_beam(mock_model):
    generator = SimpleSequenceGenerator(mock_model)
    plan = generator.result

    assert len(plan) == len(mock_model.beams)
    for step, beam in zip(plan, mock_model.beams):
        beam_guid = step.element_ids[0]
        assert beam is mock_model[beam_guid]


def test_serialize_plan(mock_model):
    generator = SimpleSequenceGenerator(mock_model)
    plan = generator.result

    plan = json_loads(json_dumps(plan))
    model = json_loads(json_dumps(mock_model))

    assert len(plan) == len(model.beams)
    for step, beam in zip(plan, model.beams):
        assert str(beam.guid) == step.element_ids[0]
