"""Tests for the side-by-side strategy comparison."""

import pytest
from synthetic import bridge_with_ground
from synthetic import portal_frame
from synthetic import stack
from synthetic import three_way_interlock
from synthetic import wall_panels

from assembly_sequencing import STRATEGIES
from assembly_sequencing import GravityStrategy
from assembly_sequencing import RandomStrategy
from assembly_sequencing import compare_strategies
from assembly_sequencing import make_strategy
from assembly_sequencing import describe_comparison
from assembly_sequencing.compare import StrategyReport


def test_the_default_comparison_covers_the_whole_registry():
    reports = compare_strategies(wall_panels())
    assert [report.name for report in reports] == sorted(STRATEGIES)


def test_strategies_are_reported_in_the_order_they_were_given():
    reports = compare_strategies(wall_panels(), ["skeleton", "gravity", "chain"])
    assert [report.name for report in reports] == ["skeleton", "gravity", "chain"]


def test_instances_and_names_are_both_accepted():
    reports = compare_strategies(stack(), [GravityStrategy(), "clearance", RandomStrategy(seed=3)])
    assert [report.name for report in reports] == ["gravity", "clearance", "random"]
    assert all(report.is_complete for report in reports)


def test_every_strategy_sees_the_same_run_settings():
    # Only the ranking may differ between rows, otherwise the table compares nothing.
    reports = compare_strategies(wall_panels(), ["gravity", "chain"], manual_set=["plate"], width=2)
    assert all("plate" in report.result.manual_set for report in reports)


def test_the_metrics_describe_the_order_that_came_out():
    report = compare_strategies(bridge_with_ground(), ["gravity"])[0]
    assert report.is_complete
    assert report.placed == report.total == 4
    assert report.chain_continuity == 1.0
    assert report.height_inversions == 0
    assert report.tight == 0
    assert report.mean_margin == pytest.approx(90.0)


def test_a_tight_fit_is_counted_and_drags_the_margin_down():
    # The state recorded is the one at the step the element was actually removed, so a
    # fixture that is tight in the complete assembly is not enough -- the portal frame
    # still has slots at the step each element comes off.
    report = compare_strategies(portal_frame(), ["gravity"])[0]
    assert report.tight > 0
    assert report.min_margin == pytest.approx(0.0)
    assert report.mean_margin < 90.0


def test_the_control_scores_worse_than_gravity_on_the_wall():
    gravity, arbitrary = compare_strategies(wall_panels(), ["gravity", RandomStrategy(seed=0)])
    assert gravity.tight < arbitrary.tight
    assert gravity.mean_margin > arbitrary.mean_margin


def test_cluster_switches_count_the_jumps_between_subassemblies():
    by_cluster, by_height = compare_strategies(wall_panels(), ["subassembly", "gravity"])
    assert by_cluster.cluster_switches <= by_height.cluster_switches


def test_a_model_that_cannot_be_sequenced_is_reported_as_unfinished():
    reports = compare_strategies(three_way_interlock(), ["gravity", "clearance"])
    assert not any(report.is_complete for report in reports)
    assert all(report.placed < report.total for report in reports)
    text = describe_comparison(reports)
    assert "No strategy completed this model" in text


def test_the_table_has_a_row_for_every_strategy():
    reports = compare_strategies(wall_panels())
    text = describe_comparison(reports)
    lines = text.splitlines()
    assert lines[0].split() == ["strategy", "done", "placed", "tight", "mean", "deg", "min", "deg", "byhand", "switches", "chain", "inversions", "unsupp"]
    for report in reports:
        assert any(line.startswith(report.name) for line in lines)


def test_the_table_can_show_the_orders_and_how_far_they_agree():
    reports = compare_strategies(wall_panels(), ["gravity", "gravity"])
    text = describe_comparison(reports, show_orders=True)
    assert "10/10 agree" in text
    assert "sill" in text


def test_a_report_keeps_the_result_it_summarizes():
    report = compare_strategies(stack(), ["gravity"])[0]
    assert isinstance(report, StrategyReport)
    assert report.order == report.result.order == ["bottom", "middle", "top"]


def test_support_inversions_counts_the_jointed_pairs_built_in_the_wrong_order():
    from assembly_sequencing import TermStrategy
    from synthetic import blocked_ridge

    data = blocked_ridge()
    # Height alone reaches past the obstructed ridge and takes the pier out from under it.
    by_height = TermStrategy(["stable", "base_z", "centroid_z"], name="by-height")
    assert _report(data, by_height).support_inversions == 1
    assert _report(data, make_strategy("gravity")).support_inversions == 0


def test_support_inversions_ignores_a_height_drop_between_unjointed_elements():
    # wall_panels finishes one bay and drops back down to start the next, which is a
    # height inversion and not a support inversion.
    reports = compare_strategies(wall_panels(), ["subassembly"])
    assert reports[0].height_inversions > 0
    assert reports[0].support_inversions == 0


def _report(data, strategy):
    return compare_strategies(data, [strategy])[0]
