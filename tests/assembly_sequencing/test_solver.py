from compas.geometry import Vector

import pytest

from assembly_sequencing import LOCKED
from assembly_sequencing import ROOMY
from assembly_sequencing import ROOMY_MARGIN
from assembly_sequencing import TIGHT
from assembly_sequencing import HalfSpace
from assembly_sequencing import Locked
from assembly_sequencing import SignedAxis
from assembly_sequencing import Solution
from assembly_sequencing import classify
from assembly_sequencing import rank_candidates
from assembly_sequencing import solve

UP = Vector(0, 0, 1)
DOWN = Vector(0, 0, -1)
EAST = Vector(1, 0, 0)
WEST = Vector(-1, 0, 0)
NORTH = Vector(0, 1, 0)


def test_no_constraints_is_free_not_locked():
    # resolve_constraints([]) used to return None, meaning locked, when zero constraints
    # means entirely free. The sequencer then papered over it with a special case.
    result = solve([])
    assert isinstance(result, Solution)
    assert result.state == ROOMY
    assert result.margin == pytest.approx(1.0)
    assert result.direction.dot(UP) == pytest.approx(1.0)


def test_single_half_space_extracts_along_its_normal():
    result = solve([HalfSpace(UP)])
    assert result.state == ROOMY
    assert result.direction.dot(UP) == pytest.approx(1.0)
    assert result.margin == pytest.approx(1.0)


def test_argmax_beats_first_hit_when_straight_up_is_merely_feasible():
    # Straight up satisfies both constraints exactly on the boundary (margin 0). The
    # bisector clears both by 45 degrees. The earlier implementation appended (0,0,1)
    # first and returned the first candidate that merely passed, so up always won
    # whenever it was feasible at all, regardless of how marginal.
    result = solve([HalfSpace(UP), HalfSpace(EAST)])
    assert result.margin == pytest.approx(0.5**0.5)
    assert result.state == ROOMY
    assert result.direction.dot(UP) == pytest.approx(0.5**0.5)
    assert result.direction.dot(EAST) == pytest.approx(0.5**0.5)


def test_direction_is_independent_of_constraint_order():
    constraints = [HalfSpace(UP), HalfSpace(EAST), HalfSpace(Vector(0.2, 0.4, 1))]
    forward = solve(constraints)
    backward = solve(list(reversed(constraints)))
    rotated = solve(constraints[1:] + constraints[:1])
    for other in (backward, rotated):
        assert other.direction.dot(forward.direction) == pytest.approx(1.0)
        assert other.margin == pytest.approx(forward.margin)


def test_slot_between_two_faces_is_tight_not_locked():
    # A beam housed between two parallel faces can still slide along them. The feasible
    # set collapses to a plane, so the margin is exactly zero -- a correct answer about a
    # genuinely tight fit, not an artifact.
    result = solve([HalfSpace(EAST), HalfSpace(WEST)])
    assert isinstance(result, Solution)
    assert result.state == TIGHT
    assert result.margin == pytest.approx(0.0)
    assert result.direction.dot(EAST) == pytest.approx(0.0)


def test_slot_prefers_vertical_among_equally_good_directions():
    # Every direction in the plane is exactly as good, so the tie-break decides, and it
    # prefers dropping the beam in vertically.
    result = solve([HalfSpace(EAST), HalfSpace(WEST)])
    assert result.direction.dot(UP) == pytest.approx(1.0)


def test_a_genuinely_empty_cone_is_locked():
    # Four inward normals that sum to zero and span space: nothing satisfies all of them.
    normals = [Vector(1, 1, 1), Vector(-1, -1, 1), Vector(1, -1, -1), Vector(-1, 1, -1)]
    result = solve([HalfSpace(n) for n in normals])
    assert isinstance(result, Locked)
    assert result.state == LOCKED
    assert result.direction is None


def test_single_axis_is_tight_and_keeps_its_direction():
    result = solve([SignedAxis(EAST)])
    assert result.state == TIGHT
    assert result.direction.dot(EAST) == pytest.approx(1.0)


def test_one_dof_is_never_roomy_however_generous_the_half_spaces():
    # A strict 1-DOF fit is a slot by definition. Surrounding half-spaces can only make it
    # worse, never roomier.
    result = solve([SignedAxis(UP), HalfSpace(UP)])
    assert result.state == TIGHT
    assert result.margin == pytest.approx(0.0)


def test_anti_parallel_axes_are_locked():
    # A genuine deadlock, not a sign mistake. abs() here would be a bug.
    result = solve([SignedAxis(UP), SignedAxis(DOWN)])
    assert isinstance(result, Locked)
    assert "1-DOF" in result.reason


def test_near_parallel_axes_are_locked():
    # Two exact 1-DOF constraints that are merely near-parallel really are
    # over-constrained; neither has any freedom to give.
    result = solve([SignedAxis(UP), SignedAxis(Vector(0.01, 0, 1))])
    assert isinstance(result, Locked)


def test_identical_axes_are_feasible():
    result = solve([SignedAxis(UP), SignedAxis(Vector(0, 0, 2))])
    assert isinstance(result, Solution)
    assert result.state == TIGHT


def test_axis_pushing_through_material_is_locked_and_the_reverse_is_not_tried():
    # The reverse direction would satisfy the half-space, but the axis is signed: only
    # +direction is permitted, so this is locked.
    result = solve([SignedAxis(UP), HalfSpace(DOWN)])
    assert isinstance(result, Locked)
    assert "pushes through material" in result.reason


def test_axis_origin_is_carried_but_does_not_affect_the_result():
    from compas.geometry import Point

    here = solve([SignedAxis(UP, origin=Point(0, 0, 0))])
    far_away = solve([SignedAxis(UP, origin=Point(1000, -50, 7))])
    assert here.direction.dot(far_away.direction) == pytest.approx(1.0)
    assert here.margin == pytest.approx(far_away.margin)


def test_unknown_constraint_type_raises():
    with pytest.raises(TypeError):
        solve([UP])


def test_inferred_constraints_are_counted():
    result = solve([HalfSpace(UP, inferred=True), HalfSpace(EAST)])
    assert result.inferred_count == 1


def test_inferred_count_survives_a_lock():
    result = solve([SignedAxis(UP, inferred=True), SignedAxis(DOWN, inferred=True)])
    assert result.inferred_count == 2


@pytest.mark.parametrize(
    "margin, expected",
    [
        (1.0, ROOMY),
        (ROOMY_MARGIN, ROOMY),
        (ROOMY_MARGIN - 1e-6, TIGHT),
        (0.0, TIGHT),
        (-1e-12, TIGHT),
        (-0.5, LOCKED),
    ],
)
def test_classify_boundaries(margin, expected):
    assert classify(margin) == expected


def test_margin_is_reported_as_an_angle():
    result = solve([HalfSpace(UP), HalfSpace(EAST)])
    assert result.angle_degrees == pytest.approx(45.0)


def test_swept_check_falls_back_to_the_next_best_candidate():
    # The argmax direction is obstructed, so the next feasible candidate by descending
    # margin is offered instead -- rather than declaring the element locked.
    constraints = [HalfSpace(UP), HalfSpace(EAST)]
    unobstructed = solve(constraints)

    def blocked(direction):
        return direction.dot(unobstructed.direction) < 0.99

    result = solve(constraints, path_check=blocked)
    assert isinstance(result, Solution)
    assert result.margin < unobstructed.margin
    assert result.state == TIGHT


def test_swept_check_can_lock_an_otherwise_free_element():
    result = solve([HalfSpace(UP)], path_check=lambda direction: False)
    assert isinstance(result, Locked)
    assert "obstructed" in result.reason


def test_swept_check_applies_to_the_one_dof_case_too():
    result = solve([SignedAxis(UP)], path_check=lambda direction: False)
    assert isinstance(result, Locked)
    assert "obstructed" in result.reason


def test_rank_candidates_is_sorted_by_descending_margin():
    ranked = rank_candidates([HalfSpace(UP).normal, HalfSpace(EAST).normal, HalfSpace(NORTH).normal])
    margins = [margin for margin, _ in ranked]
    assert margins == sorted(margins, reverse=True)


def test_repeating_a_constraint_changes_nothing():
    # A duplicate half-space is redundant, and multiplicity must not sway the result --
    # a plate jointed to twenty identical studs sees the same normal twenty times.
    once = solve([HalfSpace(UP), HalfSpace(EAST)])
    many = solve([HalfSpace(UP)] * 20 + [HalfSpace(EAST)] * 7)
    assert many.direction.dot(once.direction) == pytest.approx(1.0)
    assert many.margin == pytest.approx(once.margin)
    assert many.state == once.state


def test_duplicate_normals_do_not_inflate_the_candidate_set():
    from assembly_sequencing import candidate_directions

    assert len(candidate_directions([UP] * 50)) == 1


def test_world_axis_crosses_are_not_in_the_candidate_set():
    from assembly_sequencing import candidate_directions

    # A single normal has no pairwise cross, so the candidate set is just the normal and
    # the interior seed -- crosses against world X/Y/Z would add noise unrelated to the
    # geometry of the constraint set.
    assert len(candidate_directions([Vector(0, 0, 1)])) == 1
