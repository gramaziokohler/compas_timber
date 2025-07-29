import pytest
from compas_timber.model import TimberModel
from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import PlateTButtJoint
from compas_timber.connections import PlateLButtJoint
from compas.geometry import Polyline, Point


def test_plate_L_topos():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    cs = PlateConnectionSolver()

    topo_results = cs.find_topology(plate_a, plate_b)
    assert topo_results[0] == JointTopology.TOPO_EDGE_EDGE, "Expected L-joint topology"
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
    assert topo_results[0] == JointTopology.TOPO_EDGE_FACE, "Expected T-joint topology"
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
    assert topo_results[0] == JointTopology.TOPO_EDGE_FACE, "Expected T-joint topology"
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
    assert all(tr[0] == JointTopology.TOPO_EDGE_EDGE for tr in topo_results), "Expected all topology results to be L-joints"


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
    assert topo_results[0][0] == JointTopology.TOPO_EDGE_FACE, "Expected first topology result to be T-joint"
    assert topo_results[1][0] == JointTopology.TOPO_EDGE_EDGE, "Expected second topology result to be L-joint"
    assert topo_results[2][0] == JointTopology.TOPO_EDGE_EDGE, "Expected third topology result to be L-joint"


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PlateMiterJoint(plate_a, plate_b, **kwargs)
    joint.add_features()
    assert plate_a == joint.plate_a, "Expected joint to reference plate_a"
    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"
    assert any([plate_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to change outline_a"
    plate_a.reset()
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_simple_joint_and_reset_no_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    joint = PlateMiterJoint(plate_a, plate_b)
    joint.add_features()
    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"
    assert any([plate_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to change outline_a"
    plate_a.reset()
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_simple_miter_joint_reset_copy():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PlateMiterJoint(plate_a, plate_b, **kwargs)
    model = TimberModel()
    model.add_element(plate_a)
    model.add_element(plate_b)
    model.add_joint(joint)

    joint.add_features()
    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"
    assert any([plate_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to change outline_a"
    plate_a.reset()
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), "Expected joint to reset outline_a"
    model_copy = model.copy()
    joint_copy = list(model_copy.joints)[0]
    assert isinstance(joint_copy, PlateMiterJoint), "Expected joint copy to be a PlateMiterJoint"
    assert joint_copy.plate_a.outline_a == plate_a.outline_a, "Expected joint copy to reference the original plate_a"
    assert joint_copy.plate_b.outline_a == plate_b.outline_a, "Expected joint copy to reference the original plate_b"
    assert joint_copy.topology == JointTopology.TOPO_EDGE_EDGE, "Expected joint copy to have the same topology"


def test_simple_l_butt_joint_reset_copy():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)
    polyline_ab = plate_a.outline_b.copy()

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)
    polyline_bb = plate_b.outline_b.copy()

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PlateLButtJoint(plate_a, plate_b, **kwargs)
    model = TimberModel()
    model.add_element(plate_a)
    model.add_element(plate_b)
    model.add_joint(joint)

    joint.add_features()
    assert not plate_a.outline_a == polyline_a or not plate_a.outline_b == polyline_ab, "Expected joint to change outline_a"
    assert not plate_b.outline_a == polyline_b or not plate_b.outline_b == polyline_bb, "Expected joint to change outline_b"

    plate_a.reset()
    plate_b.reset()
    assert plate_a.outline_a == polyline_a and plate_a.outline_b == polyline_ab, "Expected to reset plate_a outlines"
    assert plate_b.outline_a == polyline_b and plate_b.outline_b == polyline_bb, "Expected to reset plate_b outlines"

    model_copy = model.copy()
    joint_copy = list(model_copy.joints)[0]
    assert isinstance(joint_copy, PlateLButtJoint), "Expected joint copy to be a PlateLButtJoint"
    assert joint_copy.plate_a.outline_a == plate_a.outline_a, "Expected joint copy to reference the original plate_a"
    assert joint_copy.plate_b.outline_a == plate_b.outline_a, "Expected joint copy to reference the original plate_b"
    assert joint_copy.topology == JointTopology.TOPO_EDGE_EDGE, "Expected joint copy to have the same topology"


def test_simple_t_butt_joint_reset_copy():
    polyline_main = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_main = Plate.from_outline_thickness(polyline_main, 1)
    polyline_main_b = plate_main.outline_b.copy()

    polyline_cross = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_cross = Plate.from_outline_thickness(polyline_cross, 1)
    polyline_cross_b = plate_cross.outline_b.copy()

    kwargs = {"topology": JointTopology.TOPO_EDGE_FACE, "a_segment_index": 0}
    joint = PlateTButtJoint(plate_main, plate_cross, **kwargs)
    model = TimberModel()
    model.add_element(plate_main)
    model.add_element(plate_cross)
    model.add_joint(joint)

    joint.add_features()
    assert plate_main.outline_a != polyline_main or plate_main.outline_b != polyline_main_b, "Expected joint to change plate_main outlines"
    assert plate_cross.outline_a == polyline_cross and plate_cross.outline_b == polyline_cross_b, "Expected joint to not change plate_cross outlines"
    plate_main.reset()
    assert plate_main.outline_a == polyline_main and plate_main.outline_b == polyline_main_b, "Expected joint to reset plate_main outlines"
    model_copy = model.copy()
    joint_copy = list(model_copy.joints)[0]
    assert isinstance(joint_copy, PlateTButtJoint), "Expected joint copy to be a PlateTButtJoint"
    assert joint_copy.main_plate.outline_a == plate_main.outline_a, "Expected joint copy to reference the original plate_main"
    assert joint_copy.cross_plate.outline_a == plate_cross.outline_a, "Expected joint copy to reference the original plate_cross"
    assert joint_copy.topology == JointTopology.TOPO_EDGE_FACE, "Expected joint copy to have the same topology"


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
        kwargs = {"topology": tr[0], "a_segment_index": tr[1][1], "b_segment_index": tr[2][1]}
        if tr[0] == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr[0] == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(tr[1][0], tr[2][0], **kwargs))
        elif tr[0] == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateTButtJoint(tr[1][0], tr[2][0], **kwargs))

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
        kwargs = {"topology": tr[0], "a_segment_index": tr[1][1], "b_segment_index": tr[2][1]}

        if tr[0] == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr[0] == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(tr[1][0], tr[2][0], **kwargs))
        elif tr[0] == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateTButtJoint(tr[1][0], tr[2][0], **kwargs))

    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], PlateTButtJoint), "Expected L-joints to be PlateButtJoint"
    assert isinstance(joints[1], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"
    assert isinstance(joints[2], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"


@pytest.fixture
def plate_model():
    """Create a basic TimberModel with two plates."""
    from compas.geometry import Polyline

    model = TimberModel()

    # Create two plates
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate1 = Plate.from_outline_thickness(polyline_a, 1)
    plate2 = Plate.from_outline_thickness(polyline_b, 1)

    model.add_element(plate1)
    model.add_element(plate2)

    return model, plate1, plate2


def test_plate_joint_create_joint_topology_solver_called_when_attributes_missing(plate_model, mocker):
    """Test that PlateConnectionSolver.find_topology IS called when PlateJointCandidate has missing segment indices."""

    model, plate1, plate2 = plate_model

    # Mock the PlateConnectionSolver.find_topology method to return expected results
    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")
    mock_find_topology.return_value = [
        JointTopology.TOPO_EDGE_EDGE,
        (plate1, 1),  # (plate, segment_index)
        (plate2, 0),  # (plate, segment_index)
        0.0,  # distance
        Point(x=5.0, y=10.0, z=0.0),
    ]

    # Convert generic plate joint to specific plate joint
    joint = PlateLButtJoint.create(model, plate1, plate2)

    # Verify the joint was created correctly
    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE

    # Verify that find_topology WAS called since a_segment_index was None
    mock_find_topology.assert_called_once_with(plate1, plate2)


def test_plate_joint_create_joint_topology_solver_not_called_when_attributes_set(plate_model, mocker):
    """Test that PlateConnectionSolver.find_topology IS called when PlateJointCandidate has missing segment indices."""

    model, plate1, plate2 = plate_model

    # Mock the PlateConnectionSolver.find_topology method
    mock_find_topology = mocker.patch.object(PlateConnectionSolver, "find_topology")

    # Convert generic plate joint to specific plate joint
    joint = PlateLButtJoint.create(model, plate1, plate2, topology=JointTopology.TOPO_EDGE_EDGE, a_segment_index=1, b_segment_index=0)

    # Verify the joint was created correctly
    assert isinstance(joint, PlateLButtJoint)
    assert joint.topology == JointTopology.TOPO_EDGE_EDGE
    assert joint.a_segment_index == 1
    assert joint.b_segment_index == 0

    # Verify that find_topology was NOT called since all attributes were already set
    mock_find_topology.assert_not_called()
