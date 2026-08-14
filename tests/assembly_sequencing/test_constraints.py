from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector

import pytest

from assembly_sequencing import HalfSpace
from assembly_sequencing import SignedAxis
from assembly_sequencing import validate_constraints


def test_half_space_is_unitized_on_construction():
    constraint = HalfSpace(Vector(0, 0, 5))
    assert constraint.normal.length == pytest.approx(1.0)


def test_half_space_accepts_a_tuple():
    assert HalfSpace((1, 0, 0)).normal.x == pytest.approx(1.0)


def test_degenerate_half_space_raises():
    with pytest.raises(ValueError):
        HalfSpace(Vector(0, 0, 0))


def test_degenerate_axis_raises():
    with pytest.raises(ValueError):
        SignedAxis(Vector(0, 0, 0))


def test_signed_axis_from_line_takes_start_to_end():
    line = Line(Point(0, 0, 0), Point(0, 0, 3))
    axis = SignedAxis.from_line(line)
    assert axis.direction.z == pytest.approx(1.0)
    assert axis.origin == Point(0, 0, 0)


def test_signed_axis_from_reversed_line_is_the_opposite_direction():
    # Signed, not bidirectional: the two ends of a Line are not interchangeable.
    forward = SignedAxis.from_line(Line(Point(0, 0, 0), Point(0, 0, 1)))
    backward = SignedAxis.from_line(Line(Point(0, 0, 1), Point(0, 0, 0)))
    assert forward.direction.dot(backward.direction) == pytest.approx(-1.0)


def test_signed_axis_allows_only_its_own_direction():
    axis = SignedAxis(Vector(0, 0, 1))
    assert axis.allows(Vector(0, 0, 1))
    assert not axis.allows(Vector(0, 0, -1))


def test_validate_passes_known_types():
    constraints = [HalfSpace(Vector(0, 0, 1)), SignedAxis(Vector(1, 0, 0))]
    assert validate_constraints(constraints) == constraints


@pytest.mark.parametrize(
    "unknown",
    [
        Vector(0, 0, 1),
        Line(Point(0, 0, 0), Point(0, 0, 1)),
        [Vector(0, 0, 1)],
        "up",
        None,
    ],
)
def test_validate_raises_on_unknown_types(unknown):
    # Dropping a constraint makes an element look more free than it is, which is the
    # dangerous direction to fail in. Raw compas geometry must go through an adapter.
    with pytest.raises(TypeError):
        validate_constraints([unknown])


def test_inferred_flag_defaults_to_false():
    assert HalfSpace(Vector(0, 0, 1)).inferred is False
    assert SignedAxis(Vector(0, 0, 1), inferred=True).inferred is True
