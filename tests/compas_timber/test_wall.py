import pytest

from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Point
from compas.geometry import Vector
from compas_timber.elements import Wall
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.utils import classify_polyline_segments
from compas_model.elements import Group


@pytest.fixture
def model():
    return TimberModel()


@pytest.fixture
def wall1():
    return Wall.from_boundary(polyline=Polyline([[0, 0, 0], [0, 100, 0], [100, 100, 0], [100, 0, 0], [0, 0, 0]]), normal=Vector.Zaxis(), thickness=10, name="wall1")


@pytest.fixture
def wall2():
    return Wall.from_boundary(polyline=Polyline([[100, 0, 0], [100, 100, 0], [200, 100, 0], [200, 0, 0], [100, 0, 0]]), normal=Vector.Zaxis(), thickness=10, name="wall2")


@pytest.fixture
def nameless_wall():
    return Wall.from_boundary(polyline=Polyline([[100, 0, 0], [100, 100, 0], [200, 100, 0], [200, 0, 0], [100, 0, 0]]), normal=Vector.Zaxis(), thickness=10)


@pytest.fixture
def beam_list():
    beam_a = Beam(Frame.worldXY(), 100, 200, 300)
    beam_b = Beam(Frame.worldXY(), 102, 240, 30)
    beam_c = Beam(Frame.worldXY(), 100, 200, 3)
    beam_d = Beam(Frame.worldXY(), 150, 20, 60)
    return [beam_a, beam_b, beam_c, beam_d]


def test_wall_groups(model, wall1, nameless_wall):
    model.add_group_element(wall1)
    model.add_group_element(nameless_wall, name="wall2")

    assert model.has_group(wall1)
    assert model.has_group(nameless_wall)


def test_add_elements_to_group(model, beam_list, wall1, wall2):
    beam_a, beam_b, beam_c, beam_d = beam_list

    wall1_group = model.add_group_element(wall1)
    wall2_group = model.add_group_element(wall2)

    model.add_element(beam_a, parent=wall1_group)
    model.add_element(beam_b, parent=wall1_group)
    model.add_element(beam_c, parent=wall2_group)
    model.add_element(beam_d, parent=wall2_group)

    assert model.has_group(wall1)
    assert model.has_group(wall2)
    assert list(model.get_elements_in_group(wall1_group)) == [wall1, beam_a, beam_b]
    assert list(model.get_elements_in_group(wall2_group)) == [wall2, beam_c, beam_d]


def test_get_elements_in_group_filter(model, beam_list, wall1, wall2):
    beam_a, beam_b, beam_c, beam_d = beam_list

    wall1_group = model.add_group_element(wall1)
    wall2_group = model.add_group_element(wall2)

    model.add_element(beam_a, parent=wall1_group)
    model.add_element(beam_b, parent=wall1_group)
    model.add_element(beam_c, parent=wall2_group)
    model.add_element(beam_d, parent=wall2_group)

    assert model.has_group(wall1)
    assert model.has_group(wall2)
    assert list(model.get_elements_in_group(wall1_group, filter_=lambda b: b.is_beam)) == [beam_a, beam_b]
    assert list(model.get_elements_in_group(wall2_group, filter_=lambda b: b.is_beam)) == [beam_c, beam_d]
    assert list(model.get_elements_in_group(wall1_group, filter_=lambda b: b.is_wall)) == [wall1]
    assert list(model.get_elements_in_group(wall2_group, filter_=lambda b: b.is_wall)) == [wall2]
    assert list(model.get_elements_in_group(wall1_group, filter_=lambda b: b.is_group_element)) == [wall1]
    assert list(model.get_elements_in_group(wall2_group, filter_=lambda b: b.is_group_element)) == [wall2]


def test_group_does_not_exist(model, wall1):
    group = Group(name="non_existent_group")
    with pytest.raises(ValueError):
        list(model.get_elements_in_group(group))
    with pytest.raises(ValueError):
        list(model.get_elements_in_group(wall1))


def test_group_already_exists(model, wall1):
    model.add_group_element(wall1)

    with pytest.raises(Exception):
        model.add_group_element(wall1)


def test_not_group_element(model):
    beam = Beam(Frame.worldXY(), 100, 200, 300)

    with pytest.raises(ValueError):
        model.add_group_element(beam)


def test_wall_with_door_openings():
    outline = Polyline(
        [
            Point(x=5.265306325014119, y=0.0, z=2.0),
            Point(x=5.265306325014119, y=0.0, z=6.0),
            Point(x=0.0, y=0.0, z=6.0),
            Point(x=0.0, y=0.0, z=0.0),
            Point(x=8.617857142857142, y=0.0, z=0.0),
            Point(x=8.617857142857144, y=0.0, z=4.0),
            Point(x=11.0, y=0.0, z=4.0),
            Point(x=10.999999999999998, y=0.0, z=0.0),
            Point(x=17.0, y=0.0, z=0.0),
            Point(x=17.0, y=0.0, z=6.0),
            Point(x=7.0, y=0.0, z=6.0),
            Point(x=7.0, y=0.0, z=2.0),
        ]
    )
    normal = Vector.Yaxis()

    outline_vertices, internal_vertex_groups = classify_polyline_segments(outline, normal)

    assert outline_vertices == [2, 3, 8, 9]
    assert internal_vertex_groups == [[4, 5, 6, 7], [10, 11, 0, 1]]


def test_wall_with_door_openings_ccw():
    outline = Polyline(
        [
            Point(x=5.265306325014119, y=0.0, z=2.0),
            Point(x=5.265306325014119, y=0.0, z=6.0),
            Point(x=0.0, y=0.0, z=6.0),
            Point(x=0.0, y=0.0, z=0.0),
            Point(x=8.617857142857142, y=0.0, z=0.0),
            Point(x=8.617857142857144, y=0.0, z=4.0),
            Point(x=11.0, y=0.0, z=4.0),
            Point(x=10.999999999999998, y=0.0, z=0.0),
            Point(x=17.0, y=0.0, z=0.0),
            Point(x=17.0, y=0.0, z=6.0),
            Point(x=7.0, y=0.0, z=6.0),
            Point(x=7.0, y=0.0, z=2.0),
        ]
    )
    normal = Vector.Yaxis() * -1.0

    outline_vertices, internal_vertex_groups = classify_polyline_segments(outline, normal, direction="ccw")

    assert outline_vertices == [2, 3, 8, 9]
    assert internal_vertex_groups == [[4, 5, 6, 7], [10, 11, 0, 1]]


def test_fu():
    polyline = Polyline(
        [
            Point(x=-3.29152931150972, y=12.978899915119495, z=0.0),
            Point(x=-3.2915293115097186, y=14.98344519542361, z=0.0),
            Point(x=-3.2915293115097186, y=14.98344519542361, z=2.5),
            Point(x=-3.291529311509721, y=11.006981997986284, z=2.5),
            Point(x=-3.291529311509721, y=11.006981997986284, z=0.0),
            Point(x=-3.29152931150972, y=12.06490942153033, z=0.0),
            Point(x=-3.2915293115097204, y=12.06490942153033, z=1.9471006966997255),
            Point(x=-3.2915293115097204, y=12.978899915119495, z=1.9471006966997255),
            Point(x=-3.29152931150972, y=12.978899915119495, z=0.0),
        ]
    )

    normal = Vector(x=1.000, y=-0.000, z=0.000)

    external, internal = classify_polyline_segments(polyline, normal, direction="ccw")
