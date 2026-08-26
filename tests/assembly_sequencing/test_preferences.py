"""Tests for the ranking strategies.

Two kinds of test here, deliberately separated:

* **Comparator tests** put two candidates in front of one strategy and check which it
  prefers. They pin the strategy's stated idea down to one sentence and fail for one
  reason.
* **Sequence tests** run the whole search and check a property of the order that comes out.
  They are the ones that would catch a strategy that ranks correctly and still produces a
  useless sequence.

The fixture with any real choice in it is :func:`synthetic.wall_panels`. The smaller ones
are so tightly constrained that feasibility decides everything and every strategy agrees,
which makes them useless for telling strategies apart -- and worth remembering before
adding a strategy test against them.

"""

import pytest
from compas.geometry import Vector
from synthetic import blocked_ridge
from synthetic import double_birdsmouth
from synthetic import slot
from synthetic import stack
from synthetic import wall_panels

from assembly_sequencing import ROOMY
from assembly_sequencing import STRATEGIES
from assembly_sequencing import TERMS
from assembly_sequencing import TIGHT
from assembly_sequencing import ChainStrategy
from assembly_sequencing import ClearanceStrategy
from assembly_sequencing import GravityStrategy
from assembly_sequencing import LayeredStrategy
from assembly_sequencing import RandomStrategy
from assembly_sequencing import RankingContext
from assembly_sequencing import SkeletonFirstStrategy
from assembly_sequencing import Solution
from assembly_sequencing import SubassemblyStrategy
from assembly_sequencing import TermStrategy
from assembly_sequencing import WeightedStrategy
from assembly_sequencing import disconnecting_elements
from assembly_sequencing import generate
from assembly_sequencing import ground_ids
from assembly_sequencing import make_strategy
from assembly_sequencing.preferences import rank

UP = Vector(0, 0, 1)


def context_for(data, active=None, last_removed=None):
    """A RankingContext for `data` with `active` still in place."""
    active = frozenset(data.element_ids if active is None else active)
    labels = {i: data.groups.get(i, "unlabelled") for i in data.element_ids}
    disconnecting = disconnecting_elements(data, active, ground_ids(data, active))
    return RankingContext(data, active, last_removed, labels, disconnecting, 0)


def roomy(margin=0.9):
    return Solution(UP, margin, ROOMY)


def tight():
    return Solution(UP, 0.0, TIGHT)


def preferred(strategy, context, candidates):
    """The element `strategy` ranks first."""
    return rank(context, candidates, strategy)[0][1]


# ---------------------------------------------------------------------------------------
# every strategy, on a model with room to disagree
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(STRATEGIES))
def test_every_registered_strategy_sequences_the_whole_model(name):
    data = wall_panels()
    result = generate(data, strategy=make_strategy(name))
    assert result.is_complete
    assert sorted(result.order) == sorted(data.element_ids)


@pytest.mark.parametrize("name", sorted(STRATEGIES))
def test_every_registered_strategy_takes_no_arguments(name):
    assert make_strategy(name).name


@pytest.mark.parametrize("name", sorted(STRATEGIES))
def test_no_strategy_puts_the_sill_anywhere_but_first(name):
    # Removing the sill strands every stud, and every strategy leads with the stability
    # term for exactly that reason.
    assert generate(wall_panels(), strategy=make_strategy(name)).order[0] == "sill"


def test_an_unknown_strategy_name_lists_the_known_ones():
    with pytest.raises(ValueError) as error:
        make_strategy("bottom-up")
    assert "gravity" in str(error.value)


# ---------------------------------------------------------------------------------------
# terms
# ---------------------------------------------------------------------------------------


def test_every_term_stays_on_the_unit_interval():
    data = wall_panels()
    strategy = TermStrategy(sorted(TERMS))
    context = context_for(data)
    ranges = strategy.ranges(data)
    for name, term in sorted(TERMS.items()):
        for element_id in data.element_ids:
            value = term(context, element_id, roomy(), ranges)
            assert 0.0 <= value <= 1.0, "{} returned {} for {}".format(name, value, element_id)


def test_a_term_that_cannot_separate_anything_goes_inert():
    # Every element in `slot` starts at z=0, so the span is empty and the term must not
    # invent an ordering -- or divide by zero.
    data = slot()
    strategy = TermStrategy(["base_z"])
    context = context_for(data)
    scores = set(strategy.score(context, i, roomy()) for i in data.element_ids)
    assert scores == {(0.5,)}


def test_a_term_name_can_be_inverted_with_a_minus():
    data = wall_panels()
    context = context_for(data)
    upright = TermStrategy(["base_z"])
    inverted = TermStrategy(["-base_z"])
    assert preferred(upright, context, {"plate": roomy(), "sill": roomy()}) == "plate"
    assert preferred(inverted, context, {"plate": roomy(), "sill": roomy()}) == "sill"


def test_an_unknown_term_is_named_in_the_error():
    with pytest.raises(ValueError) as error:
        TermStrategy(["height"])
    assert "height" in str(error.value)
    assert "base_z" in str(error.value)


def test_a_strategy_needs_at_least_one_term():
    with pytest.raises(ValueError):
        TermStrategy([])


def test_the_margin_term_survives_a_locked_result():
    # Intrinsic locks reach ranking as Locked results whose margin is NaN. A NaN in the
    # sort key compares false against everything and would scramble the order silently.
    result = generate(double_birdsmouth(), strategy=ClearanceStrategy())
    assert result.is_complete
    assert sorted(result.order) == ["plate", "rafter", "strut_east", "strut_west"]


def test_normalization_is_recomputed_for_a_different_model():
    strategy = TermStrategy(["base_z"])
    first = wall_panels()
    second = stack()
    assert strategy.ranges(first) is strategy.ranges(first)
    assert strategy.ranges(second) is not strategy.ranges(first)
    assert strategy.ranges(second).spans["base_z"] == (0.0, 2.0)


# ---------------------------------------------------------------------------------------
# what each strategy actually prefers
# ---------------------------------------------------------------------------------------


def test_gravity_takes_the_higher_element_even_when_it_is_tight():
    context = context_for(wall_panels())
    candidates = {"header_a": tight(), "stud_a1": roomy()}
    assert preferred(GravityStrategy(), context, candidates) == "header_a"


def test_gravity_leaves_alone_an_element_that_is_still_carrying_something():
    # The pier stands higher than the cleat and gravity would normally say so, but the
    # ridge is jointed to the pier and still up there on it. Read forwards: the ridge must
    # not go into the model before the pier it sits on.
    data = blocked_ridge()
    candidates = {"pier": roomy(), "cleat": roomy()}
    assert preferred(GravityStrategy(), context_for(data), candidates) == "cleat"


def test_gravity_goes_back_to_height_once_nothing_is_left_on_top():
    # The same two candidates and the opposite answer, with only the ridge taken away:
    # the term speaks about what is still standing, not about the pair.
    data = blocked_ridge()
    context = context_for(data, active=set(data.element_ids) - {"ridge"})
    candidates = {"pier": roomy(), "cleat": roomy()}
    assert preferred(GravityStrategy(), context, candidates) == "pier"


def test_gravity_reaches_past_height_when_the_tallest_candidate_is_carrying_something():
    # The whole point of the fixture: the ridge is obstructed, so the highest element the
    # ranking can see is the pier -- and the pier is holding the ridge up. Sorting by
    # height alone takes the pier; gravity takes the cleat, which frees the ridge next
    # step and gets the ridge into the model after the pier rather than before it.
    data = blocked_ridge()
    order = generate(data, strategy=GravityStrategy()).order
    assert order.index("pier") < order.index("ridge")
    assert order.index("post") < order.index("ridge")
    assert order == ["pad", "post", "pier", "ridge", "cleat"]


def test_gravity_yields_the_precedence_rather_than_getting_stuck():
    # Every element is carrying another, so no candidate is ever clear above. The term
    # goes quiet and the sequence still completes rather than reporting a dead end.
    data = stack()
    result = generate(data, strategy=GravityStrategy())
    assert result.is_complete
    assert result.order == ["bottom", "middle", "top"]


def test_clearance_takes_the_roomier_element_even_when_it_is_lower():
    # The same two candidates as above, and the opposite answer: this is the whole
    # difference between the two strategies, in one comparison.
    context = context_for(wall_panels())
    candidates = {"header_a": tight(), "stud_a1": roomy()}
    assert preferred(ClearanceStrategy(), context, candidates) == "stud_a1"


def test_clearance_separates_two_roomy_candidates_by_margin():
    context = context_for(wall_panels())
    candidates = {"stud_a1": roomy(margin=0.2), "stud_b1": roomy(margin=0.8)}
    assert preferred(ClearanceStrategy(), context, candidates) == "stud_b1"


def test_skeleton_takes_the_short_peripheral_element_first():
    # Removed first in disassembly is placed last in assembly, so this is the statement
    # that the long, well-connected plate is placed early.
    context = context_for(wall_panels())
    candidates = {"plate": roomy(), "stud_a1": roomy()}
    assert preferred(SkeletonFirstStrategy(), context, candidates) == "stud_a1"


def test_skeleton_places_the_plate_far_earlier_than_gravity_does():
    data = wall_panels()
    skeleton = generate(data, strategy=SkeletonFirstStrategy()).order
    gravity = generate(data, strategy=GravityStrategy()).order
    assert skeleton.index("plate") < gravity.index("plate")


def test_subassembly_stays_in_the_cluster_it_is_working_on():
    context = context_for(wall_panels(), last_removed="stud_a1")
    candidates = {"stud_a2": roomy(), "stud_b1": roomy()}
    assert preferred(SubassemblyStrategy(), context, candidates) == "stud_a2"


def test_subassembly_finishes_one_bay_before_starting_the_next():
    order = generate(wall_panels(), strategy=SubassemblyStrategy()).order
    positions = [index for index, element_id in enumerate(order) if element_id.startswith("stud_a") or element_id == "header_a"]
    assert positions == list(range(min(positions), min(positions) + len(positions)))


def test_chain_prefers_a_neighbour_of_the_last_element_moved():
    data = wall_panels()
    context = context_for(data, last_removed="header_a")
    # header_a's neighbours are the bay-a studs; stud_b1 is two hops away through the sill.
    candidates = {"stud_a1": roomy(), "stud_b1": roomy()}
    assert preferred(ChainStrategy(), context, candidates) == "stud_a1"


def test_layered_treats_one_course_as_a_tie_and_lets_continuity_decide():
    data = wall_panels()
    strategy = LayeredStrategy(tolerance=1.0)
    context = context_for(data, last_removed="stud_a1")
    # Both studs are in the same course, so the band term ties and the cluster term wins.
    assert preferred(strategy, context, {"stud_a2": roomy(), "stud_b2": roomy()}) == "stud_a2"


def test_layered_never_goes_back_down_a_course():
    data = wall_panels()
    strategy = LayeredStrategy(tolerance=1.0)
    order = generate(data, strategy=strategy).order
    ranges = strategy.ranges(data)
    bands = [strategy.band(data.base_z[i], ranges) for i in order]
    assert bands == sorted(bands)


def test_layered_derives_its_course_height_when_none_is_given():
    data = wall_panels()
    strategy = LayeredStrategy(bands=2)
    ranges = strategy.ranges(data)
    assert strategy.band(data.base_z["sill"], ranges) == 0.0
    assert strategy.band(data.base_z["plate"], ranges) == 1.0


def test_layered_rejects_a_course_height_that_cannot_band_anything():
    with pytest.raises(ValueError):
        LayeredStrategy(tolerance=0.0)
    with pytest.raises(ValueError):
        LayeredStrategy(bands=0)


# ---------------------------------------------------------------------------------------
# the tunable ones
# ---------------------------------------------------------------------------------------


def test_a_weight_decides_which_term_wins():
    context = context_for(wall_panels())
    candidates = {"header_a": tight(), "stud_a1": roomy()}
    assert preferred(WeightedStrategy({"base_z": 1.0, "roomy": 0.1}), context, candidates) == "header_a"
    assert preferred(WeightedStrategy({"base_z": 1.0, "roomy": 10.0}), context, candidates) == "stud_a1"


def test_a_negative_weight_and_a_minus_prefix_mean_the_same_thing():
    context = context_for(wall_panels())
    candidates = {"plate": roomy(), "sill": roomy()}
    assert preferred(WeightedStrategy({"base_z": -1.0}), context, candidates) == "sill"
    assert preferred(WeightedStrategy({"-base_z": 1.0}), context, candidates) == "sill"


def test_a_weighted_strategy_scores_to_a_single_number():
    context = context_for(wall_panels())
    score = WeightedStrategy({"stable": 10.0, "base_z": 1.0}).score(context, "plate", roomy())
    assert len(score) == 1


def test_a_weighted_strategy_needs_a_weight():
    with pytest.raises(ValueError):
        WeightedStrategy({})


def test_weights_can_reproduce_a_bottom_up_sequence():
    data = wall_panels()
    tuned = WeightedStrategy({"stable": 100.0, "base_z": 10.0, "centroid_z": 5.0, "roomy": 1.0}, name="tuned")
    result = generate(data, strategy=tuned)
    assert result.is_complete
    assert result.order[0] == "sill"
    assert result.order[-1] == "plate"


# ---------------------------------------------------------------------------------------
# the control
# ---------------------------------------------------------------------------------------


def test_the_random_control_is_the_same_on_every_run():
    data = wall_panels()
    first = generate(data, strategy=RandomStrategy(seed=7)).order
    second = generate(data, strategy=RandomStrategy(seed=7)).order
    assert first == second


def test_a_different_seed_is_a_different_sequence():
    data = wall_panels()
    orders = set(tuple(generate(data, strategy=RandomStrategy(seed=seed)).order) for seed in range(6))
    assert len(orders) > 1


def test_the_random_control_still_respects_stability():
    for seed in range(6):
        assert generate(wall_panels(), strategy=RandomStrategy(seed=seed)).order[0] == "sill"


def test_gravity_beats_the_random_control_on_tight_fits():
    # The point of shipping a control: a strategy that scores no better than an arbitrary
    # order on a model is not earning its place there.
    data = wall_panels()
    gravity = generate(data, strategy=GravityStrategy())
    arbitrary = generate(data, strategy=RandomStrategy(seed=0))
    assert len(gravity.tight_fits) < len(arbitrary.tight_fits)
