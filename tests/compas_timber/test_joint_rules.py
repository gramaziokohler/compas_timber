from email import errors
import pytest
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import PlateTButtJoint
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections import PlateMiterJoint
from compas_timber.elements import Beam
from compas_timber.elements import Plate
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
    joints,errors = JointRule.joints_from_rules_and_elements(rules, beams)
    assert len(joints) == 4


def test_joints_from_beams_and_rules_with_max_distance(separated_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules)
    assert len(joint_defs) == 0
    assert len(unmatched_pairs) == 4
    joints,errors = JointRule.joints_from_rules_and_elements(rules, separated_beams)
    assert len(joints) == 0

    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.15),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules)
    assert len(joint_defs) == 1
    assert len(unmatched_pairs) == 3
    joints,errors = JointRule.joints_from_rules_and_elements(rules, separated_beams)
    assert len(joints) == 1

    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.05),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joint_defs_from_beams_and_rules(separated_beams, rules, max_distance=0.15)
    assert len(joint_defs) == 3
    assert len(unmatched_pairs) == 1
    joints,errors = JointRule.joints_from_rules_and_elements(rules, separated_beams, max_distance=0.15)
    assert len(joints) == 3

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
    joints, errors = JointRule.joints_from_rules_and_elements(rules, L_beams)
    assert len(joints) == 3


def test_different_rules_max_distance(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    joint_defs, _ = JointRule.joint_defs_from_beams_and_rules(L_beams_separated, rules)
    joints_names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert len(joint_defs) == 0
    joints, errors = JointRule.joints_from_rules_and_elements(rules, L_beams_separated)
    assert len(joints) == 0

    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.15)]
    joint_defs, _ = JointRule.joint_defs_from_beams_and_rules(L_beams_separated, rules)
    joints_names = set([joint_def.joint_type.__name__ for joint_def in joint_defs])
    assert joints_names == set(["LMiterJoint"])
    assert len(joint_defs) == 3
    joints, errors = JointRule.joints_from_rules_and_elements(rules, L_beams_separated)
    assert len(joints) == 3


def test_plate_topo_rules():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    rules = [
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints,errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"

def test_plate_category_rules():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    plate_a.attributes["category"] = "A"

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)
    plate_b.attributes["category"] = "B"

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    plate_c = Plate.from_outline_thickness(polyline_c, 1)
    plate_c.attributes["category"] = "C"

    rules = [
        CategoryRule(PlateTButtJoint, "A", "B"),
        CategoryRule(PlateMiterJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
    ]
    joints, errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 2, "Expected two joints"

    plate_a.reset()
    plate_b.reset()
    plate_c.reset()

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateMiterJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
    ]
    joints, errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])

def test_plate_rules_priority():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    plate_a.attributes["category"] = "A"

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)
    plate_b.attributes["category"] = "B"

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    plate_c = Plate.from_outline_thickness(polyline_c, 1)
    plate_c.attributes["category"] = "C"

    rules = [
        DirectRule(PlateLButtJoint, [plate_c, plate_b]),
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateMiterJoint, "A", "C"),
        CategoryRule(PlateMiterJoint, "B", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints, errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints, errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint"]), "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints, errors = JointRule.joints_from_rules_and_elements(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"
