"""Overrides: the manual set as an input, pinned order, and staleness reporting."""

from synthetic import bridge_with_ground
from synthetic import double_birdsmouth
from synthetic import portal_frame
from synthetic import stack
from synthetic import three_way_interlock
from synthetic import with_excluded

from assembly_sequencing import generate


def test_generate_is_idempotent():
    first = generate(portal_frame())
    second = generate(portal_frame())
    assert first.order == second.order
    assert first.manual_set == second.manual_set


def test_feeding_the_manual_set_back_reproduces_the_same_order():
    # The round trip the override workflow depends on: propose, amend, re-run.
    data = double_birdsmouth()
    first = generate(data)
    second = generate(data, manual_set=first.manual_set)
    assert second.order == first.order
    assert second.manual_set == first.manual_set
    assert second.staleness.is_empty


def test_intrinsic_locks_are_added_to_a_user_manual_set_rather_than_replacing_it():
    result = generate(double_birdsmouth(), manual_set={"strut_west"})
    assert "strut_west" in result.manual_set
    assert {"plate", "rafter"} <= result.manual_set


def test_a_user_manual_set_rescues_a_dead_end():
    # A human can rotate, tilt and spring a member into place, so robot kinematics do not
    # apply to elements in the manual set.
    stuck = generate(three_way_interlock())
    assert not stuck.is_complete

    rescued = generate(three_way_interlock(), manual_set={"beta"})
    assert rescued.is_complete
    assert len(rescued.order) == 3


def test_manual_elements_may_carry_no_insertion_vector():
    result = generate(three_way_interlock(), manual_set={"beta"})
    # Locked but hand-placed: the honest answer is that there is no robot vector for it.
    assert result.insertion_vectors["beta"] is None
    assert result.state("beta") == "locked"


def test_a_pin_is_honoured():
    result = generate(stack(), pinned_order={"top": 0})
    assert result.is_complete
    assert result.pin_conflict is None
    assert result.order[0] == "top"


def test_a_pin_overrides_the_preference_ranking():
    unpinned = generate(stack())
    assert unpinned.order == ["bottom", "middle", "top"]
    pinned = generate(stack(), pinned_order={"top": 0})
    assert pinned.order != unpinned.order


def test_a_full_pinned_list_is_reproduced_exactly():
    wanted = ["ground", "link", "far", "tip"]
    result = generate(bridge_with_ground(), pinned_order=wanted)
    assert result.is_complete
    assert result.order == wanted


def test_a_pinned_list_can_reverse_the_default_order():
    wanted = ["tip", "far", "link", "ground"]
    result = generate(bridge_with_ground(), pinned_order=wanted)
    assert result.is_complete
    assert result.order == wanted


def test_an_impossible_pin_is_reported_not_silently_resolved():
    # The rafter is locked while both posts stand, so it cannot be the last thing placed.
    data = portal_frame()
    result = generate(data, pinned_order={"rafter": len(data.element_ids) - 1})
    assert result.pin_conflict is not None
    assert result.pin_conflict.element_id == "rafter"
    assert result.pin_conflict.assembly_index == 3
    assert not result.is_complete


def test_a_pin_conflict_explains_itself():
    data = portal_frame()
    result = generate(data, pinned_order={"rafter": 3})
    assert "cannot be extracted" in result.pin_conflict.reason


def test_a_deleted_pinned_element_produces_a_staleness_report():
    result = generate(stack(), pinned_order={"demolished_beam": 0})
    assert not result.staleness.is_empty
    entries = list(result.staleness)
    assert entries[0][0] == "pin"
    assert entries[0][1] == "demolished_beam"
    assert "no longer" in entries[0][2] or "not in the model" in entries[0][2]
    # The rest of the run still happens; only the instruction that no longer applies is
    # dropped, and never without saying so.
    assert result.is_complete


def test_a_deleted_hand_placed_element_produces_a_staleness_report():
    result = generate(stack(), manual_set={"demolished_beam"})
    assert len(result.staleness) == 1
    kind, element_id, message = list(result.staleness)[0]
    assert kind == "manual"
    assert element_id == "demolished_beam"
    assert "no longer in the model" in message
    assert result.is_complete


def test_a_pin_outside_the_model_range_is_reported():
    result = generate(stack(), pinned_order={"top": 99})
    assert len(result.staleness) == 1
    assert "outside" in list(result.staleness)[0][2]
    assert result.is_complete


def test_a_shorter_pinned_list_reports_that_the_model_grew():
    # New elements appeared under an override, so the caller is told the plan no longer
    # covers the model rather than being left to wonder.
    result = generate(stack(), pinned_order=["bottom"])
    assert not result.staleness.is_empty
    assert "the model has 3" in list(result.staleness)[0][2]
    assert result.is_complete


def test_two_pins_on_the_same_position_report_the_dropped_one():
    result = generate(stack(), pinned_order={"top": 0, "middle": 0})
    messages = [message for _, _, message in result.staleness]
    assert any("already pinned" in message for message in messages)


def test_an_override_on_an_excluded_element_is_reported():
    result = generate(with_excluded(), manual_set={"sheathing"})
    kind, element_id, message = list(result.staleness)[0]
    assert kind == "manual"
    assert element_id == "sheathing"
    assert "excluded" in message


def test_a_pin_on_an_excluded_element_is_reported():
    result = generate(with_excluded(), pinned_order={"screw_1": 0})
    assert "excluded" in list(result.staleness)[0][2]


def test_staleness_describes_itself():
    result = generate(stack(), manual_set={"gone"}, pinned_order={"also_gone": 0})
    text = result.staleness.describe()
    assert "gone" in text
    assert "also_gone" in text
    assert len(result.staleness) == 2


def test_a_clean_run_reports_no_staleness():
    result = generate(stack(), manual_set={"middle"}, pinned_order={"bottom": 0})
    assert result.staleness.is_empty
    assert result.staleness.describe() == "No stale overrides."


def test_result_describes_itself():
    text = generate(double_birdsmouth()).describe()
    assert "by hand" in text
    assert "insert" in text
