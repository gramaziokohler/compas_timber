import pytest
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import Frame

from compas_timber.design import JointRuleSolver
from compas_timber.design import get_clusters_from_model
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import LFrenchRidgeLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import PlateTButtJoint
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import JointCandidate
from compas_timber.connections import PlateJointCandidate
from compas_timber.connections import Cluster
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.design import DirectRule
from compas_timber.design import CategoryRule
from compas_timber.design import TopologyRule
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
    1 <=> 2:L
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
    1 <=> 2:L
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


@pytest.fixture
def Y_beams():
    """
    0 <=> 1:L
    1 <=> 2:L
    2 <=> 3:L

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(0, 0, 0), Point(1, 0, 0)),
        Line(Point(0, 0, 0), Point(0, 1, 0)),
        Line(Point(0, 0, 0), Point(-1, -1, 0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def K_beams():
    """
    0 <=> 1:Y
    1 <=> 2:Y
    2 <=> 3:Y

    """
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(0, 0, 0), Point(1, 0, 0)),
        Line(Point(0, -1, 0), Point(0, 1, 0)),
        Line(Point(0, 0, 0), Point(-1, -1, 0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


def test_joints_from_beams_and_rules_with_no_max_distance(separated_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    model = TimberModel()
    model.add_elements(separated_beams)
    solver = JointRuleSolver(rules)
    with pytest.raises(ValueError):
        errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 0


def test_joints_from_beams_and_rules_with_max_distance_rule(separated_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.15),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    model = TimberModel()
    model.add_elements(separated_beams)
    solver = JointRuleSolver(rules)
    _, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 1
    assert len(unjoined_clusters) == 3


def test_joints_from_beams_and_rules_with_max_distance_model(separated_beams):
    model = TimberModel()
    model.add_elements(separated_beams)
    rules = [
        TopologyRule(JointTopology.TOPO_L, LMiterJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint, max_distance=0.05),
        TopologyRule(JointTopology.TOPO_X, XLapJoint),
    ]
    model = TimberModel()
    model.add_elements(separated_beams)
    solver = JointRuleSolver(rules, max_distance=0.15)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 3
    assert len(unjoined_clusters) == 1


def test_direct_rule_matches_cluster(beams):
    rule = DirectRule(LMiterJoint, beams[:2])
    cluster_a = Cluster([JointCandidate(*beams[:2])])
    cluster_b = Cluster([JointCandidate(*beams[1:3])])
    assert rule._matches_cluster(cluster_a) is True
    assert rule._matches_cluster(cluster_b) is False


def test_direct_rule_get_joint(beams):
    rules = [
        DirectRule(LMiterJoint, [beams[0], beams[1]]),
        DirectRule(LMiterJoint, [beams[2], beams[3]]),
        DirectRule(TButtJoint, [beams[2], beams[1]]),
        DirectRule(XLapJoint, [beams[3], beams[0]]),
    ]
    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver(rules)
    _, _ = solver.apply_rules_to_model(model)
    assert set([j.__class__.__name__ for j in model.joints]) == set(["LMiterJoint", "TButtJoint", "XLapJoint"])


def test_joint_type_check_elements_compatibility(beams):
    rules = [DirectRule(LMiterJoint, [beams[0], beams[1]])]
    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 1


def test_joint_type_check_elements_compatibility_bad_normal(beams):
    new_frame = Frame(beams[1].frame.point, beams[1].frame.xaxis, Vector(1, 1, 1))
    new_beam = Beam(frame=new_frame, length=beams[1].length, width=beams[1].width, height=beams[1].height)
    beams[1] = new_beam  # replace beam 1 with a beam with a different frame

    rules = [DirectRule(LFrenchRidgeLapJoint, [beams[0], beams[1]])]

    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(errors) == 1
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 0


def test_joint_type_check_elements_compatibility_bad_dims(beams):
    rules = [DirectRule(LFrenchRidgeLapJoint, [beams[0], beams[1]])]
    beams[1]._width = 0.25
    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(errors) == 1
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 0


def test_direct_rule_try_get_joint_max_distance_failed(separated_beams):
    rule = DirectRule(LMiterJoint, [separated_beams[0], separated_beams[1]], max_distance=0.05)
    model = TimberModel()
    model.add_elements(separated_beams)
    solver = JointRuleSolver([rule], max_distance=0.15)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(errors) == 1
    assert len(list(model.joints)) == 0


def test_direct_rule_try_get_joint_max_distance_success(separated_beams):
    rule = DirectRule(LMiterJoint, [separated_beams[0], separated_beams[1]], max_distance=0.15)
    model = TimberModel()
    model.add_elements(separated_beams)
    solver = JointRuleSolver([rule])
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(errors) == 0
    assert len(list(model.joints)) == 1


def test_category_rule_try_get_joint(beams):
    for beam in beams:
        beam.attributes["category"] = "A"
    beams[1].attributes["category"] = "B"
    rule = CategoryRule(LMiterJoint, "A", "B")
    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver([rule])
    errors, unjoined_clusters = solver.apply_rules_to_model(model)

    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 1


def test_category_rule_same_category(beams):
    main = beams[2]
    cross = beams[1]
    for beam in beams:
        beam.attributes["category"] = "A"
    rule = CategoryRule(TButtJoint, "A", "A")
    model = TimberModel()
    model.add_elements([cross, main])
    solver = JointRuleSolver([rule])
    _, _ = solver.apply_rules_to_model(model)
    joint = list(model.joints)[0]
    assert joint.main_beam == main
    assert joint.cross_beam == cross

    model = TimberModel()
    model.add_elements([main, cross])
    solver = JointRuleSolver([rule])
    _, _ = solver.apply_rules_to_model(model)
    joint = list(model.joints)[0]
    assert joint.main_beam == main
    assert joint.cross_beam == cross


def test_topology_rule_try_get_joint(beams):
    rule = TopologyRule(JointTopology.TOPO_L, LMiterJoint)
    model = TimberModel()
    model.add_elements(beams)
    solver = JointRuleSolver([rule])
    _, _ = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 2


def test_mixed_rules(L_beams):
    for beam in L_beams:
        beam.attributes["category"] = "A"
    L_beams[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    model = TimberModel()
    model.add_elements(L_beams)
    solver = JointRuleSolver(rules)
    _, _ = solver.apply_rules_to_model(model)
    assert len(model.joints) == 3
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LLapJoint", "LButtJoint", "LMiterJoint"])


def test_different_rules_max_distance(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    model = TimberModel()
    model.add_elements(L_beams_separated)
    solver = JointRuleSolver(rules)
    with pytest.raises(ValueError):
        errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 0


def test_different_rules_max_distance_on_topo_rule(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint, max_distance=0.15)]
    model = TimberModel()
    model.add_elements(L_beams_separated)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    # TopologyRule overrides CategoryRule when the latter fails to make a joint, but DirectRule raises error and is not overridden
    assert len([j for j in model.joints if not isinstance(j, JointCandidate)]) == 2
    assert len(unjoined_clusters) == 2
    assert len(errors) == 1  # error because DirectRule fails
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LMiterJoint"])  # TopologyRule has generated the joint


def test_different_rules_max_distance_on_category_rule(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B", max_distance=0.15), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    model = TimberModel()
    model.add_elements(L_beams_separated)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 1
    assert len(unjoined_clusters) == 3
    assert len(errors) == 1  # error because CategoryRule fails
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LButtJoint"])  # CategoryRule has generated the joint


def test_different_rules_max_distance_on_direct_rule(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2], max_distance=0.15), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    model = TimberModel()
    model.add_elements(L_beams_separated)
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 1
    assert len(unjoined_clusters) == 3
    assert len(errors) == 0  # NO error because DirectRule succeeds
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LLapJoint"])  # DirectRule has generated the joint


def test_different_rules_max_distance_on_rule_solver(L_beams_separated):
    for beam in L_beams_separated:
        beam.attributes["category"] = "A"
    L_beams_separated[1].attributes["category"] = "B"
    rules = [DirectRule(LLapJoint, L_beams_separated[:2]), CategoryRule(LButtJoint, "A", "B"), TopologyRule(JointTopology.TOPO_L, LMiterJoint)]
    model = TimberModel()
    model.add_elements(L_beams_separated)
    solver = JointRuleSolver(rules, max_distance=0.15)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 3
    assert len(unjoined_clusters) == 1
    assert len(errors) == 0
    assert set([joint.__class__.__name__ for joint in model.joints]) == set(["LLapJoint", "LButtJoint", "LMiterJoint"])  # All rules have generated the joints


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
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, PlateJointCandidate)]) == 3, "Expected three joints"


def test_plate_category_rules_reverse_topo():
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
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)

    assert len([j for j in model.joints if not isinstance(j, PlateJointCandidate)]) == 2, "Expected two joints"


def test_plate_category_rules_correct_topo():
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
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateMiterJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
    ]
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len([j for j in model.joints if not isinstance(j, PlateJointCandidate)]) == 3, "Expected three joints"


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
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in model.joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), (
        "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"
    )

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        CategoryRule(PlateLButtJoint, "B", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in model.joints]) == set(["PlateLButtJoint", "PlateTButtJoint"]), "Expected PlateLButtJoint, PlateTButtJoint"

    rules = [
        CategoryRule(PlateTButtJoint, "B", "A"),
        CategoryRule(PlateLButtJoint, "A", "C"),
        TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
        TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
    ]
    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(model.joints) == 3, "Expected three joints"
    assert set([j.__class__.__name__ for j in model.joints]) == set(["PlateLButtJoint", "PlateTButtJoint", "PlateMiterJoint"]), (
        "Expected PlateLButtJoint, PlateTButtJoint, and PlateMiterJoint"
    )


def test_joints_created_with_y_topo_cluster(Y_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LButtJoint),
    ]
    model = TimberModel()
    model.add_elements(Y_beams)

    clusters = get_clusters_from_model(model)
    assert len(clusters) == 1
    assert clusters[0].topology == JointTopology.TOPO_Y
    assert len(clusters[0].joints) == 3

    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(unjoined_clusters) == 0
    assert len(model.joints) == 3
    assert all([isinstance(j, LButtJoint) for j in model.joints])


def test_joints_created_with_k_topo_cluster(K_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_L, LButtJoint),
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
    ]
    model = TimberModel()
    model.add_elements(K_beams)

    clusters = get_clusters_from_model(model)
    assert len(clusters) == 1
    assert clusters[0].topology == JointTopology.TOPO_K
    assert len(clusters[0].joints) == 3

    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(unjoined_clusters) == 0
    assert len(model.joints) == 3
    assert any([isinstance(j, LButtJoint) for j in model.joints])
    assert any([isinstance(j, TButtJoint) for j in model.joints])


def test_joints_created_with_k_topo_cluster_l_fails(K_beams):
    rules = [
        TopologyRule(JointTopology.TOPO_T, TButtJoint),
    ]
    model = TimberModel()
    model.add_elements(K_beams)

    clusters = get_clusters_from_model(model)
    assert len(clusters) == 1
    assert clusters[0].topology == JointTopology.TOPO_K
    assert len(clusters[0].joints) == 3

    solver = JointRuleSolver(rules)
    errors, unjoined_clusters = solver.apply_rules_to_model(model)
    assert len(unjoined_clusters) == 1
    assert len(model.joints) == 2
    assert all([isinstance(j, TButtJoint) for j in model.joints])
