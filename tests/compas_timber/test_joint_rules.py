import pytest
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import LMiterJoint
from compas_timber.elements import Beam
from compas_timber.design import JointRule
from compas_timber.design import DirectRule
from compas_timber.design import CategoryRule
from compas_timber.design import TopologyRule


@pytest.fixture
def beams():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(-1, 0, 0), Point(1, 0, 0)),
        Line(Point(1, 0, 0), Point(1, 2, 0)),
        Line(Point(1, 1, 0), Point(0, 1, 0)),
        Line(Point(0, 1, 0), Point(0, -1, 0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def separated_beams():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(-1, 0, 0), Point(1, 0, 0)),
        Line(Point(1, 0, 0.1), Point(1, 2, 0.1)),
        Line(Point(1, 1, 0), Point(0, 1, 0)),
        Line(Point(0, 1, 0.1), Point(0, -1, 0.1)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def L_beams():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(-1, 0, 0), Point(1, 0, 0)),
        Line(Point(1, 0, 0), Point(1, 1, 0)),
        Line(Point(1, 1, 0), Point(0, 1, 0)),
        Line(Point(0, 1, 0), Point(0, -1, 0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def L_beams_separated():
    """
    0 <=> 1:L
    1 <=> 2:T
    2 <=> 3:L
    3 <=> 0:X

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(-1, 0, 0), Point(1, 0, 0)),
        Line(Point(1, 0, 0.1), Point(1, 1, 0.1)),
        Line(Point(1, 1, 0), Point(0, 1, 0)),
        Line(Point(0, 1, 0.1), Point(0, -1, 0.1)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


def test_joints_from_beams_and_topo_rules(beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(beams, rules)
    assert len(joint_defs) == 4
    assert len(unmatched_pairs) == 0
    names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert names == set(["LMiterJoint", "TButtJoint", "XLapJoint"])


def test_joints_from_beams_and_rules_with_max_distance(separated_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules)
    assert len(joint_defs) == 0
    assert len(unmatched_pairs) == 4

    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.15),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules)
    assert len(joint_defs) == 1
    assert len(unmatched_pairs) == 3

    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.05),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules, max_distance=0.15)
    assert len(joint_defs) == 3
    assert len(unmatched_pairs) == 1


def test_direct_rule_contains(beams):
    rule = DirectRule(LMiterJoint, beams[:2])
    assert rule.contains(beams[:2]) is True
    assert rule.contains(beams[1:3]) is False
    assert rule.contains(beams[2:]) is False
    assert rule.contains([beams[0], beams[3]]) is False


def test_direct_rule_comply(beams):
    rule = DirectRule(LMiterJoint, [beams[0], beams[1]])
    assert rule.comply([beams[0], beams[1]]) is True
    assert rule.comply([beams[2], beams[3]]) is True
    assert rule.comply([beams[1], beams[2]]) is True
    assert rule.comply([beams[3], beams[0]]) is True


def test_direct_rule_comply_max_distance(separated_beams):
    rule = DirectRule(LMiterJoint, [separated_beams[0], separated_beams[1]], max_distance=0.05)
    assert rule.comply([separated_beams[0], separated_beams[1]]) is False
    assert rule.comply([separated_beams[2], separated_beams[3]]) is False
    assert rule.comply([separated_beams[1], separated_beams[2]]) is False
    assert rule.comply([separated_beams[3], separated_beams[0]]) is False


def test_category_rule_comply(beams):
    for beam in beams:
        beam.attributes["category"] = "A"
    beams[1].attributes["category"] = "B"
    rule = CategoryRule(LMiterJoint, "A", "B")
    assert rule.comply(beams[:2]) is True
    assert rule.comply(beams[2:]) is False


def test_topology_rule_comply(beams):
    rule = TopologyRule(JointTopology.TOPO_L, LMiterJoint)
    assert rule.comply([beams[0], beams[1]])[0] is True
    assert rule.comply([beams[1], beams[2]])[0] is False
    assert rule.comply([beams[2], beams[3]])[0] is True
    assert rule.comply([beams[3], beams[0]])[0] is False


def test_different_rules(L_beams):
    for beam in L_beams:
        beam.attributes["category"] = "A"
    L_beams[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(L_beams, rules)
    joints_names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert joints_names == set(["LLapJoint", "LButtJoint", "LMiterJoint"])
    assert len(joint_defs) == 3


def test_different_rules_max_distance(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(L_beams_separated, rules)
    joints_names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert len(joint_defs) == 0

    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.15)]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(L_beams_separated, rules)
    joints_names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert joints_names == set(["LMiterJoint"])
    assert len(joint_defs) == 3
