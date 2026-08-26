import pytest
from synthetic import ball_node
from synthetic import bridge_with_ground
from synthetic import dense_lattice
from synthetic import double_birdsmouth
from synthetic import portal_frame
from synthetic import stack
from synthetic import three_way_interlock

from assembly_sequencing import build_blocking_graph
from assembly_sequencing import disconnecting_elements
from assembly_sequencing import extract
from assembly_sequencing import fully_blocked
from assembly_sequencing import ground_ids
from assembly_sequencing import intrinsic_locks
from assembly_sequencing import order_dependent_locks
from assembly_sequencing import strongly_connected_components
from assembly_sequencing import subassemblies


def all_ids(data):
    return set(data.element_ids)


def test_blocking_edges_are_pairwise_precedences():
    data = double_birdsmouth()
    graph = build_blocking_graph(data)
    assert graph["rafter"] == {"plate"}
    assert graph["plate"] == {"rafter"}
    assert graph["strut_west"] == set()
    assert graph["strut_east"] == set()


def test_double_birdsmouth_is_an_intrinsic_lock():
    data = double_birdsmouth()
    clusters = intrinsic_locks(build_blocking_graph(data))
    assert clusters == [frozenset(["plate", "rafter"])]


def test_intrinsic_lock_survives_cutting_the_model_down_to_the_pair():
    # That is what makes it intrinsic rather than order-dependent.
    data = double_birdsmouth()
    pair = {"plate", "rafter"}
    assert not extract(data, "plate", pair).is_feasible
    assert not extract(data, "rafter", pair).is_feasible


def test_portal_frame_has_no_intrinsic_locks():
    # Three of its four elements are locked in the complete assembly, and every one of
    # those locks is a fact about the order rather than about the design. None of them may
    # be reported as hand placement.
    data = portal_frame()
    assert intrinsic_locks(build_blocking_graph(data)) == []


def test_portal_frame_is_blocked_in_the_complete_assembly():
    data = portal_frame()
    blocked = fully_blocked(data)
    assert set(blocked) == {"post_west", "post_east", "rafter"}
    assert all(not result.is_feasible for result in blocked.values())


def test_order_dependent_locks_exclude_intrinsic_members():
    data = double_birdsmouth()
    graph = build_blocking_graph(data)
    clusters = intrinsic_locks(graph)
    order_dependent = order_dependent_locks(data, all_ids(data), clusters)
    assert "plate" not in order_dependent
    assert "rafter" not in order_dependent


def test_three_way_interlock_has_no_pairwise_edge_to_find():
    # Sound but not complete: every pair separates, so the up-front pass reports nothing
    # and the search is left to discover the dead end.
    data = three_way_interlock()
    graph = build_blocking_graph(data)
    assert all(blockers == set() for blockers in graph.values())
    assert intrinsic_locks(graph) == []
    assert set(fully_blocked(data)) == all_ids(data)


def test_n_ary_joint_contributes_precedence():
    # Nothing in this fixture is a two-element joint. An implementation that skips joints
    # without exactly two members sees three free elements and no precedence at all.
    data = ball_node()
    assert not extract(data, "trapped", all_ids(data)).is_feasible
    assert extract(data, "trapped", {"trapped", "lower"}).is_feasible
    assert extract(data, "trapped", {"trapped", "upper"}).is_feasible


def test_scc_on_a_hand_built_graph():
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"c"}, "e": set()}
    assert strongly_connected_components(graph) == [["a", "b", "c"], ["d"], ["e"]]


def test_scc_ignores_edges_to_nodes_outside_the_graph():
    graph = {"a": {"b", "gone"}, "b": {"a"}}
    assert strongly_connected_components(graph) == [["a", "b"]]


def test_scc_handles_a_long_chain_without_recursing():
    # Rhino's CPython shares Python's recursion limit; a recursive Tarjan would blow up.
    size = 5000
    graph = {i: {i + 1} for i in range(size)}
    graph[size] = set()
    components = strongly_connected_components(graph)
    assert len(components) == size + 1


def test_subassembly_labels_are_identical_across_runs():
    # Label propagation broke ties on (count, guid), and since guids are random the labels
    # -- and therefore the whole ranking -- differed between runs on identical input.
    data = double_birdsmouth()
    first = subassemblies(data, build_blocking_graph(data))
    second = subassemblies(data, build_blocking_graph(data))
    assert first == second


def test_subassembly_labels_do_not_depend_on_element_order():
    data = double_birdsmouth()
    reversed_data = double_birdsmouth()
    reversed_data.element_ids = list(reversed(reversed_data.element_ids))
    assert subassemblies(data, build_blocking_graph(data)) == subassemblies(reversed_data, build_blocking_graph(reversed_data))


def test_intrinsic_cluster_members_share_a_subassembly():
    data = double_birdsmouth()
    labels = subassemblies(data, build_blocking_graph(data))
    assert labels["plate"] == labels["rafter"]
    assert labels["strut_west"] != labels["plate"]


def test_declared_groups_win_over_inferred_clusters():
    data = double_birdsmouth()
    data.groups = {"plate": "wall", "rafter": "roof"}
    labels = subassemblies(data, build_blocking_graph(data))
    assert labels["plate"] == "wall"
    assert labels["rafter"] == "roof"


def test_ground_ids_are_the_lowest_elements():
    data = stack()
    assert ground_ids(data, all_ids(data)) == {"bottom"}


def test_ground_ids_follow_the_shrinking_active_set():
    data = stack()
    assert ground_ids(data, {"middle", "top"}) == {"middle"}


def test_disconnecting_elements_finds_the_articulation_points():
    data = bridge_with_ground()
    assert disconnecting_elements(data, all_ids(data), {"ground"}) == {"ground", "link", "far"}


def test_an_end_element_disconnects_nothing():
    data = bridge_with_ground()
    assert "tip" not in disconnecting_elements(data, all_ids(data), {"ground"})


def test_an_already_ungrounded_component_is_not_blamed_on_a_removal():
    data = bridge_with_ground()
    # Nothing in this active set touches the ground, so no removal *creates* the condition.
    assert disconnecting_elements(data, {"far", "tip"}, set()) == set()


def test_no_articulation_points_in_a_cycle():
    data = ball_node()
    assert disconnecting_elements(data, all_ids(data), {"lower", "upper"}) == set()


def test_removing_the_only_grounded_element_strands_everything():
    # Not an articulation point, but its removal still leaves a component with no support.
    data = ball_node()
    assert disconnecting_elements(data, all_ids(data), {"lower"}) == {"lower"}


def test_a_lone_element_strands_nothing_when_it_is_the_whole_assembly():
    data = ball_node()
    assert disconnecting_elements(data, {"lower"}, {"lower"}) == set()


def test_swept_check_can_block_an_element_free_by_its_joints():
    # In a dense lattice a beam can be kinematically free per its joints while its
    # extraction path passes straight through a beam it is not jointed to -- and the joint
    # constraints alone would report a clean vector with a comfortable margin.
    data = dense_lattice()
    without_obstacle = extract(data, "flyer", {"flyer", "anchor"})
    with_obstacle = extract(data, "flyer", {"flyer", "anchor", "obstacle"})
    assert without_obstacle.direction.x == pytest.approx(0.5**0.5)
    assert with_obstacle.is_feasible
    assert with_obstacle.direction.z == pytest.approx(1.0)
    assert with_obstacle.margin < without_obstacle.margin


def test_swept_check_locks_an_element_with_no_clear_direction_left():
    data = dense_lattice(seal_off_flyer=True)
    result = extract(data, "flyer", {"flyer", "anchor", "obstacle"})
    assert not result.is_feasible
    assert "obstructed" in result.reason


def test_blocking_graph_respects_a_reduced_active_set():
    data = double_birdsmouth()
    graph = build_blocking_graph(data, active_ids={"strut_west", "plate"})
    assert set(graph) == {"strut_west", "plate"}
    assert graph["plate"] == set()


def test_the_ground_is_a_level_and_not_a_single_lowest_element():
    # Feet cut to sit on one slab differ by a fraction of a millimetre in the lowest
    # corner of their boxes. All three are on the ground; grounding only the lowest one
    # would leave the other two a step away from being stranded.
    from synthetic import _table_input

    ids = ["foot_a", "foot_b", "foot_c", "cap"]
    neighbors = {"foot_a": {"cap"}, "foot_b": {"cap"}, "foot_c": {"cap"}, "cap": {"foot_a", "foot_b", "foot_c"}}
    data = _table_input(
        ids,
        neighbors,
        {},
        base_z={"foot_a": 0.0, "foot_b": 0.2, "foot_c": 0.4, "cap": 2000.0},
        centroid_z={"foot_a": 1000.0, "foot_b": 1000.0, "foot_c": 1000.0, "cap": 2000.0},
    )
    assert ground_ids(data) == {"foot_a", "foot_b", "foot_c"}
    assert disconnecting_elements(data, set(ids), ground_ids(data)) == set()


def test_a_tighter_ground_tolerance_can_still_be_asked_for():
    from synthetic import _table_input

    ids = ["foot_a", "foot_b"]
    data = _table_input(
        ids,
        {"foot_a": {"foot_b"}, "foot_b": {"foot_a"}},
        {},
        base_z={"foot_a": 0.0, "foot_b": 0.2},
        centroid_z={"foot_a": 1000.0, "foot_b": 1000.0},
    )
    assert ground_ids(data, tolerance=0.05) == {"foot_a"}
