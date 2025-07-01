from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import PlateButtJoint
from compas.geometry import Polyline, Point


def test_plate_L_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_a, plate_b)
    assert topo_results[0] == JointTopology.TOPO_L, "Expected L-joint topology"
    assert topo_results[1][0] == plate_a, "Expected plate_a as first plate in topology result"
    assert topo_results[2][0] == plate_b, "Expected plate_b as second plate in topology result"
    assert topo_results[1][1] == 1, "Expected connection segment at index = 1"
    assert topo_results[2][1] == 0, "Expected connection segment at index = 0"


def test_plate_T_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_a, plate_b)
    assert topo_results[0] == JointTopology.TOPO_T, "Expected T-joint topology"
    assert topo_results[1][0] == plate_b, "Expected plate_a as first plate in topology result"
    assert topo_results[2][0] == plate_a, "Expected plate_b as second plate in topology result"
    assert topo_results[1][1] == 0, "Expected connection segment at index = 1"
    assert topo_results[2][1] is None, "Expected connection segment at index = 0"


def test_reversed_plate_T_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_b, plate_a)
    assert topo_results[0] == JointTopology.TOPO_T, "Expected T-joint topology"
    assert topo_results[1][0] == plate_b, "Expected plate_a as first plate in topology result"
    assert topo_results[2][0] == plate_a, "Expected plate_b as second plate in topology result"
    assert topo_results[1][1] == 0, "Expected connection segment at index = 1"
    assert topo_results[2][1] is None, "Expected connection segment at index = 0"


def test_three_plate_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    topo_results = []

    cs = PlateConnectionSolver()

    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    assert len(topo_results) == 3, "Expected three topology results"
    assert all(tr[0] == JointTopology.TOPO_L for tr in topo_results), "Expected all topology results to be L-joints"


def test_three_plate_mix_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    topo_results = []

    cs = PlateConnectionSolver()

    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    assert len(topo_results) == 3, "Expected three topology results"
    assert topo_results[0][0] == JointTopology.TOPO_T, "Expected first topology result to be T-joint"
    assert topo_results[1][0] == JointTopology.TOPO_L, "Expected second topology result to be L-joint"
    assert topo_results[2][0] == JointTopology.TOPO_L, "Expected third topology result to be L-joint"


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    joint = PlateMiterJoint(plate_a, plate_b, JointTopology.TOPO_L, 1, 0)
    joint.add_features()
    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"
    assert any([plate_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to change outline_a"
    plate_a.reset()
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_three_plate_joints():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    joints = []
    for tr in topo_results:
        if tr[0] == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr[0] == JointTopology.TOPO_L:
            joints.append(PlateMiterJoint(tr[1][0], tr[2][0], tr[0], tr[1][1], tr[2][1]))
        elif tr[0] == JointTopology.TOPO_T:
            joints.append(PlateButtJoint(tr[1][0], tr[2][0], tr[0], tr[1][1], tr[2][1]))

    assert len(joints) == 3, "Expected three joints"
    assert all(isinstance(j, PlateMiterJoint) for j in joints), "Expected L-joints to be PlateMiterJoint"


def test_three_plate_joints_mix_topo():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(plate_a, plate_b))
    topo_results.append(cs.find_topology(plate_c, plate_b))
    topo_results.append(cs.find_topology(plate_a, plate_c))

    joints = []
    for tr in topo_results:
        if tr[0] == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr[0] == JointTopology.TOPO_L:
            joints.append(PlateMiterJoint(tr[1][0], tr[2][0], tr[0], tr[1][1], tr[2][1]))
        elif tr[0] == JointTopology.TOPO_T:
            joints.append(PlateButtJoint(tr[1][0], tr[2][0], tr[0], tr[1][1], tr[2][1]))

    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], PlateButtJoint), "Expected L-joints to be PlateButtJoint"
    assert isinstance(joints[1], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"
    assert isinstance(joints[2], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"
