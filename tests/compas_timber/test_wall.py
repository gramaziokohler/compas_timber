import pytest

from compas.geometry import Frame
from compas_timber.elements import Wall
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def model():
    return TimberModel()


@pytest.fixture
def beam_list():
    beam_a = Beam(Frame.worldXY(), 100, 200, 300)
    beam_b = Beam(Frame.worldXY(), 102, 240, 30)
    beam_c = Beam(Frame.worldXY(), 100, 200, 3)
    beam_d = Beam(Frame.worldXY(), 150, 20, 60)
    return [beam_a, beam_b, beam_c, beam_d]


def test_wall_groups(model):
    wall1 = Wall(5000, 200, 3000, name="wall1")
    wall2 = Wall(3000, 200, 3000)

    model.add_group_element(wall1)
    model.add_group_element(wall2, name="wall2")

    assert model.has_group("wall1")
    assert model.has_group("wall2")


def test_add_elements_to_group(model, beam_list):
    beam_a, beam_b, beam_c, beam_d = beam_list
    wall1 = Wall(5000, 200, 3000, name="wall1")
    wall2 = Wall(3000, 200, 3000, name="wall2")

    wall1_group = model.add_group_element(wall1)
    wall2_group = model.add_group_element(wall2)

    model.add_element(beam_a, parent=wall1_group)
    model.add_element(beam_b, parent=wall1_group)
    model.add_element(beam_c, parent=wall2_group)
    model.add_element(beam_d, parent=wall2_group)

    assert model.has_group("wall1")
    assert model.has_group("wall2")
    assert list(model.get_elements_in_group("wall1")) == [wall1, beam_a, beam_b]
    assert list(model.get_elements_in_group("wall2")) == [wall2, beam_c, beam_d]


def test_get_elements_in_group_filter(model, beam_list):
    beam_a, beam_b, beam_c, beam_d = beam_list

    wall1 = Wall(5000, 200, 3000, name="wall1")
    wall2 = Wall(3000, 200, 3000, name="wall2")

    wall1_group = model.add_group_element(wall1)
    wall2_group = model.add_group_element(wall2)

    model.add_element(beam_a, parent=wall1_group)
    model.add_element(beam_b, parent=wall1_group)
    model.add_element(beam_c, parent=wall2_group)
    model.add_element(beam_d, parent=wall2_group)

    assert model.has_group("wall1")
    assert model.has_group("wall2")
    assert list(model.get_elements_in_group("wall1", filter_=lambda b: b.is_beam)) == [beam_a, beam_b]
    assert list(model.get_elements_in_group("wall2", filter_=lambda b: b.is_beam)) == [beam_c, beam_d]


def test_group_does_not_exist(model):
    with pytest.raises(ValueError):
        list(model.get_elements_in_group("non_existent_group"))


def test_group_already_exists(model):
    wall1 = Wall(5000, 200, 3000, name="wall1")

    model.add_group_element(wall1)

    with pytest.raises(ValueError):
        model.add_group_element(wall1)


def test_not_group_element(model):
    beam = Beam(Frame.worldXY(), 100, 200, 300)

    with pytest.raises(ValueError):
        model.add_group_element(beam)
