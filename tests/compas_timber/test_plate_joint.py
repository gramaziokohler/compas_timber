from compas.data import json_dumps, json_loads

from compas_timber.model import TimberModel

from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections import PlateTButtJoint
from compas.geometry import Polyline, Point


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PlateMiterJoint(plate_a, plate_b, **kwargs)
    joint.add_extensions()
    for plate in joint.elements:
        plate.apply_edge_extensions()
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
    joint.add_extensions()
    msg = "Expected outline_a to be unchanged before apply_edge_extensions"
    assert all([plate_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(plate_a.outline_a.points))]), msg
    for plate in joint.elements:
        plate.apply_edge_extensions()
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
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateLButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))

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
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateLButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))

    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], PlateLButtJoint), "Expected L-joints to be PlateButtJoint"
    assert isinstance(joints[1], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"
    assert isinstance(joints[2], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"


def test_copy_three_plate_joints_mix_topo():
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

    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    model_joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            model_joints.append(
                PlateMiterJoint.create(model, tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index)
            )
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            model_joints.append(
                PlateTButtJoint.create(model, tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index)
            )
    for j in model.joints:
        j.add_extensions()
    for p in [plate_a, plate_b, plate_c]:
        p.apply_edge_extensions()
    for j in model.joints:
        j.add_features()

    assert len(model_joints) == 3, "Expected three joints"
    assert isinstance(model_joints[0], PlateTButtJoint), "Expected L-joints to be PlateButtJoint"
    assert isinstance(model_joints[1], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"
    assert isinstance(model_joints[2], PlateMiterJoint), "Expected L-joints to be PlateMiterJoint"

    copy_model = json_loads(json_dumps(model))
    copy_joints = list(copy_model.joints)

    for j in copy_joints:
        j.add_extensions()
    for p in copy_model.plates:
        p.apply_edge_extensions()
    for j in copy_joints:
        j.add_features()

    assert len(copy_joints) == 3, "Expected three joints"
    assert set(j.__class__ for j in copy_joints) == {PlateTButtJoint, PlateMiterJoint}, "Expected joints to be PlateButtJoint and PlateMiterJoint"
