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
from compas_timber.connections import GenericJoint
from compas_timber.connections import Cluster
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.design import JointRule
from compas_timber.design import DirectRule
from compas_timber.design import CategoryRule
from compas_timber.design import TopologyRule
from compas_timber.errors import BeamJoiningError
from compas_timber.model import TimberModel


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
    model = TimberModel()
    model.add_elements(beams)
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    errors, unjoined_clusters = JointRule.joints_from_rules_and_model(rules, model)
    assert len(model.joints) == 4
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LMiterJoint", "TButtJoint", "XLapJoint"])


def test_joints_from_beams_and_rules_with_max_distance(separated_beams):
    model = TimberModel()
    model.add_elements(separated_beams)
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    with pytest.raises(ValueError):
        errors, unjoined_clusters = JointRule.joints_from_rules_and_model(rules, model)
    assert len(model.joints) == 0

    model = TimberModel()
    model.add_elements(separated_beams)
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.15),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    errors, unjoined_clusters = JointRule.joints_from_rules_and_model(rules, model)
    assert len(model.joints) == 4
    assert len(unjoined_clusters) == 3

    model = TimberModel()
    model.add_elements(separated_beams)
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.05),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    errors, unjoined_clusters = JointRule.joints_from_rules_and_model(rules, model, max_distance=0.15)
    assert len(model.joints) == 4
    assert len(unjoined_clusters) == 1

def test_direct_rule_matches_cluster(beams):
    rule = DirectRule(LMiterJoint, beams[:2])
    cluster_a = Cluster([GenericJoint(*beams[:2])])
    cluster_b = Cluster([GenericJoint(*beams[1:3])])
    assert rule._matches_cluster(cluster_a) is True
    assert rule._matches_cluster(cluster_b) is False


def test_direct_rule_get_joint(beams):
    rule = DirectRule(LMiterJoint, [beams[0], beams[1]])
    assert rule.get_joint() is not None
    rule = DirectRule(LMiterJoint, [beams[2], beams[3]])
    assert rule.get_joint() is not None
    rule = DirectRule(TButtJoint, [beams[2], beams[1]])
    assert rule.get_joint() is not None
    rule = DirectRule(XLapJoint, [beams[3], beams[0]])
    assert rule.get_joint() is not None


def test_direct_rule_get_joint_max_distance(separated_beams):
    rule = DirectRule(LMiterJoint, [separated_beams[0], separated_beams[1]], max_distance=0.05)
    with pytest.raises(BeamJoiningError):
        rule.get_joint()
    rule = DirectRule(LMiterJoint, [separated_beams[0], separated_beams[1]], max_distance=0.15)
    assert rule.get_joint() is not None


def test_category_rule_try_get_joint(beams):
    for beam in beams:
        beam.attributes["category"] = "A"
    beams[1].attributes["category"] = "B"
    rule = CategoryRule(LMiterJoint, "A", "B")
    assert rule.try_get_joint(beams[:2]) is not None
    assert rule.try_get_joint(beams[2:]) is None


def test_topology_rule_try_get_joint(beams):
    rule = TopologyRule(JointTopology.TOPO_L, LMiterJoint)
    assert rule.try_get_joint([beams[0], beams[1]]) is not None
    assert rule.try_get_joint([beams[1], beams[2]]) is None
    assert rule.try_get_joint([beams[2], beams[3]]) is not None
    assert rule.try_get_joint([beams[3], beams[0]]) is None


def test_different_rules(L_beams):
    for beam in L_beams:
        beam.attributes["category"] = "A"
    L_beams[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    joints, errors = JointRule.joints_from_rules_and_model(rules, L_beams)
    assert len(joints) == 3
    assert set([joint.__class__.__name__ for joint in joints]) == set(["LLapJoint", "LButtJoint", "LMiterJoint"])


def test_different_rules_max_distance(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    joints, errors = JointRule.joints_from_rules_and_model(rules, L_beams_separated)
    assert len(joints) == 0

    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.15)]

    joints, errors = JointRule.joints_from_rules_and_model(rules, L_beams_separated)
    assert len(joints) == 3
    assert set([joint.__class__.__name__ for joint in joints]) == set(["LMiterJoint"])


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
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])
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
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 2, "Expected two joints"

    plate_a.reset()
    plate_b.reset()
    plate_c.reset()

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateMiterJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
    ]
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])


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
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), (
        "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"
    )

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint"]), "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    joints, errors = JointRule.joints_from_rules_and_model(rules, [plate_a, plate_b, plate_c])
    assert len(joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), (
        "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"
    )
