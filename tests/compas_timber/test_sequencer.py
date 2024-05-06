import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame

from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.planning import SimpleSequenceGenerator


@pytest.fixture
def mock_assembly():
    assembly = TimberModel()
    b1 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b3 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b4 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    b5 = Beam(Frame.worldXY(), length=2.0, width=0.1, height=0.1)
    for b in [b1, b2, b3, b4, b5]:
        assembly.add_beam(b)
    return assembly


def test_simple_sequence_generator(mock_assembly):
    generator = SimpleSequenceGenerator(mock_assembly)
    plan = generator.result

    assert len(plan) == len(mock_assembly.beams)
    for step, beam in zip(plan, mock_assembly.beams):
        assert str(beam.guid) == step.element_ids[0]


def test_simple_sequence_generator_get_beam(mock_assembly):
    generator = SimpleSequenceGenerator(mock_assembly)
    plan = generator.result

    assert len(plan) == len(mock_assembly.beams)
    for step, beam in zip(plan, mock_assembly.beams):
        beam_guid = step.element_ids[0]
        assert beam is mock_assembly.elementdict[beam_guid]


def test_serialize_plan(mock_assembly):
    generator = SimpleSequenceGenerator(mock_assembly)
    plan = generator.result

    plan = json_loads(json_dumps(plan))
    assembly = json_loads(json_dumps(mock_assembly))

    assert len(plan) == len(assembly.beams)
    for step, beam in zip(plan, assembly.beams):
        assert str(beam.guid) == step.element_ids[0]
