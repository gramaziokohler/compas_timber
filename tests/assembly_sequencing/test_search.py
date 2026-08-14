import pytest
from synthetic import ball_node
from synthetic import bridge_with_ground
from synthetic import dense_lattice
from synthetic import double_birdsmouth
from synthetic import portal_frame
from synthetic import slot
from synthetic import stack
from synthetic import three_way_interlock
from synthetic import with_excluded

from assembly_sequencing import ROOMY
from assembly_sequencing import TIGHT
from assembly_sequencing import HeuristicStrategy
from assembly_sequencing import beam_search
from assembly_sequencing import generate


def test_a_simple_stack_is_sequenced_bottom_up():
    assert generate(stack()).order == ["bottom", "middle", "top"]


def test_insertion_vectors_are_the_negated_extraction_vectors():
    result = generate(stack())
    extraction = result.extraction["top"].direction
    insertion = result.insertion_vectors["top"]
    assert insertion.dot(extraction) == pytest.approx(-1.0)
    assert insertion.length == pytest.approx(1.0)


def test_every_element_gets_a_position_and_a_vector():
    result = generate(bridge_with_ground())
    assert len(result.order) == len(bridge_with_ground().element_ids)
    assert all(result.insertion_vectors[i] is not None for i in result.order)


def test_stability_ranks_above_height():
    # Removing "ground" or "link" would strand the elements beyond them, so the free end
    # comes off first even though every element is kinematically free.
    assert generate(bridge_with_ground()).order == ["ground", "link", "far", "tip"]


def test_n_ary_precedence_is_honoured():
    # "trapped" is locked while both its partners are present, so one of them must come off
    # first in disassembly -- which puts "trapped" earlier in the assembly order.
    result = generate(ball_node())
    assert result.is_complete
    assert result.order.index("trapped") < result.order.index("upper")


def test_a_tight_fit_is_sequenced_rather_than_rejected():
    from assembly_sequencing import extract

    data = slot()
    # Tight in the complete assembly: the margin is exactly zero and it is still feasible.
    assert extract(data, "dropped", set(data.element_ids)).state == TIGHT

    result = generate(data)
    assert result.is_complete
    # The recorded state is the one at the step the element was actually removed, which is
    # the vector a robot would use -- by then one neighbour has gone and there is room.
    assert result.state("dropped") == ROOMY
    assert result.order == ["left", "dropped", "right"]


def test_intrinsic_locks_are_reported_before_sequencing_and_still_sequenced():
    result = generate(double_birdsmouth())
    assert result.intrinsic_locks == [frozenset(["plate", "rafter"])]
    assert result.is_complete
    assert set(result.order) == {"plate", "rafter", "strut_west", "strut_east"}


def test_intrinsic_lock_members_are_proposed_for_hand_placement():
    result = generate(double_birdsmouth())
    assert {"plate", "rafter"} <= result.proposed_manual_set
    assert {"plate", "rafter"} <= result.manual_set


def test_order_dependent_locks_are_never_proposed_as_hand_placement():
    # Three of the four elements are locked at step zero. Not one of them is a hand
    # placement -- a mis-ordered element must not be indistinguishable from one that
    # physically needs hands.
    result = generate(portal_frame())
    assert result.intrinsic_locks == []
    assert result.is_complete
    for element_id in ("post_west", "post_east", "rafter"):
        assert result.insertion_vectors[element_id] is not None


def test_search_routes_around_an_order_dependent_lock():
    result = generate(portal_frame())
    # Only the sill can move in the complete assembly, so it must be removed first, which
    # puts it last in the assembly order.
    assert result.order[-1] == "sill"


def test_a_dead_end_produces_a_structured_report():
    result = generate(three_way_interlock())
    assert not result.is_complete
    assert result.stuck is not None
    assert result.stuck.step_index == 0
    assert result.stuck.remaining == ["alpha", "beta", "gamma"]
    assert all(reason for reason in result.stuck.blockers.values())
    assert "1-DOF" in result.stuck.blockers["alpha"]


def test_a_dead_end_is_not_an_intrinsic_lock_claim():
    # The up-front pass found nothing, so the honest report is "no order found", not
    # "no order exists".
    result = generate(three_way_interlock())
    assert result.intrinsic_locks == []
    assert result.proposed_manual_set == set()


def test_stuck_report_describes_itself():
    result = generate(three_way_interlock())
    text = result.stuck.describe()
    assert "step 0" in text
    assert "alpha" in text


def test_manual_exemption_is_what_rescues_the_intrinsic_lock():
    # Without the exemption the search has nowhere to go once the free struts are gone.
    data = double_birdsmouth()
    order, _, stuck, conflict = beam_search(data, manual_set=set())
    assert conflict is None
    assert stuck is not None
    assert stuck.step_index == 2
    assert sorted(stuck.remaining) == ["plate", "rafter"]
    assert len(order) == 2


def test_the_swept_check_shapes_the_reported_vector_not_just_the_order():
    result = generate(dense_lattice())
    assert result.is_complete
    # "obstacle" outranks "flyer" on height and comes off first, so by the time the flyer
    # moves the path is clear and the roomy bisector is reported.
    assert result.extraction["flyer"].state == ROOMY


def test_excluded_elements_are_reported_and_not_sequenced():
    result = generate(with_excluded())
    assert result.order == ["beam_low", "beam_high"]
    assert set(result.excluded) == {"sheathing", "screw_1"}
    assert "fastener" in result.excluded["screw_1"]


def test_generate_is_deterministic():
    first = generate(portal_frame())
    second = generate(portal_frame())
    assert first.order == second.order
    assert first.subassemblies == second.subassemblies


def test_generate_does_not_depend_on_element_iteration_order():
    forward = generate(portal_frame())
    shuffled = portal_frame()
    shuffled.element_ids = list(reversed(shuffled.element_ids))
    assert generate(shuffled).order == forward.order


def test_beam_width_one_still_produces_a_valid_order():
    narrow = generate(bridge_with_ground(), width=1)
    assert narrow.is_complete
    assert set(narrow.order) == set(bridge_with_ground().element_ids)


def test_wider_beam_does_not_break_the_easy_cases():
    assert generate(stack(), width=25).order == ["bottom", "middle", "top"]


def test_an_injected_strategy_replaces_the_ranking_entirely():
    data = bridge_with_ground()
    lengths = {"ground": 4.0, "link": 3.0, "far": 2.0, "tip": 1.0}
    strategy = HeuristicStrategy(lambda element_id: lengths[element_id], name="longest_first")
    result = generate(data, strategy=strategy)
    # Highest score is removed first in disassembly, so it lands last in assembly.
    assert result.order == ["tip", "far", "link", "ground"]


def test_an_empty_model_sequences_to_nothing():
    data = with_excluded()
    data.element_ids = []
    data._id_set = set()
    result = generate(data)
    assert result.order == []
    assert result.is_complete


def test_inferred_constraints_are_surfaced_in_the_result():
    from compas.geometry import Vector

    from assembly_sequencing import HalfSpace
    from assembly_sequencing import SequencingInput

    def constraints(element_id, active):
        if not active:
            return []
        return [HalfSpace(Vector(0, 0, 1), inferred=True)]

    data = SequencingInput(
        element_ids=["a", "b"],
        neighbors={"a": {"b"}, "b": {"a"}},
        base_z={"a": 0.0, "b": 1.0},
        centroid_z={"a": 0.5, "b": 1.5},
        length={"a": 1.0, "b": 1.0},
        constraints=constraints,
    )
    result = generate(data)
    # A result that depended on guesses says so.
    assert result.inferred_total == 1
    assert result.extraction["b"].inferred_count == 1
