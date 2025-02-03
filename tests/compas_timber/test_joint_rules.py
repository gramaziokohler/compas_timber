import os

import compas
import pytest
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import TLapJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import find_neighboring_beams
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.connections import JointTopology


import pytest
from compas.geometry import Line, Point
from compas_timber.elements import Beam
from compas_timber.connections import LMiterJoint, TButtJoint, XLapJoint
from compas_timber.design import JointRule, DirectRule, CategoryRule, TopologyRule

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

def test_joints_from_beams_and_topo_rules(beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    joint_defs, unmatched_pairs = JointRule.joints_from_beams_and_rules(beams, rules)
    assert len(joint_defs) == 4
    assert len(unmatched_pairs) == 0
    assert joint_defs[0].type == "LMiterJoint"
    assert joint_defs[1].type == "TButtJoint"
    assert joint_defs[2].type == "LMiterJoint"
    assert joint_defs[3].type == "XLapJoint"



def test_joints_from_beams_and_rules_with_max_distance(beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.2),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.2),
        TopologyRule(JointTopology.TOPO_X, XLapJoint, max_distance=0.2),
    ]
    joint_defs, unmatched_pairs = JointRule.joints_from_beams_and_rules(beams, rules, max_distance=0.5)
    assert len(joint_defs) == 0
    assert len(unmatched_pairs) == 4

    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.5),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.5),
        TopologyRule(JointTopology.TOPO_X, XLapJoint, max_distance=0.5),
    ]
    joint_defs, unmatched_pairs = JointRule.joints_from_beams_and_rules(beams, rules, max_distance=0.2)
    assert len(joint_defs) == 4
    assert len(unmatched_pairs) == 0



def test_direct_rule_contains(beams):
    rule = DirectRule(LMiterJoint, beams[:2])
    assert rule.contains(beams[:2]) is True
    assert rule.contains(beams[1:3]) is False
    assert rule.contains(beams[2:]) is False
    assert rule.contains([beams[0],beams[3]]) is False

def test_direct_rule_comply(beams):
    rule = DirectRule(LMiterJoint, beams[:2], max_distance=0.5)
    assert rule.comply(beams[:2]) is True
    assert rule.comply(beams[2:]) is False

def test_category_rule_comply(beams):
    for beam in beams:
        beam.attributes["category"] = "A"
    beams[1].attributes["category"] = "B"
    rule = CategoryRule(LMiterJoint, "A", "B")
    assert rule.comply(beams[:2]) is True
    assert rule.comply(beams[2:]) is False

def test_topology_rule_comply(beams):
    rule = TopologyRule(JointTopology.TOPO_L, LMiterJoint)
    assert rule.comply(beams[:2])[0] is True
    assert rule.comply(beams[2:])[0] is False
