from compas.data import json_dumps, json_loads

from compas_timber.model import TimberModel

from compas_timber.elements import Plate
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import PlateLButtJoint
from compas_timber.connections import PlateTButtJoint
from compas.geometry import Polyline, Point


def _ordered_plates(px, py, topo_data):
    """Orders `px`/`py` to match `topo_data.ordered_guids()` (edge/main first) -- PlateJoint's edge/face
    handling assumes plate_a is always the edge/main plate, same invariant `PlateConnectionSolver.create_joint_candidate`
    already enforces when building a `JointCandidate`.
    """
    plates_by_guid = {str(px.guid): px, str(py.guid): py}
    return tuple(plates_by_guid[guid] for guid in topo_data.ordered_guids())


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


def test_miter_joint_parallel_plates():
    """PlateMiterJoint between two coplanar (parallel) plates joining on one edge.

    Regression test: when the plates' faces are parallel, intersection_plane_plane(a_planes[0], b_planes[0])
    returns None, so the miter plane must fall back to the plane perpendicular to the plates.
    """
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(10, 0, 0), Point(10, 10, 0), Point(20, 10, 0), Point(20, 0, 0), Point(10, 0, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 2, "b_segment_index": 0}
    joint = PlateMiterJoint(plate_a, plate_b, **kwargs)
    joint.add_extensions()
    for plate in joint.elements:
        plate.apply_edge_extensions()

    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"


def test_miter_joint_parallel_plates_gap():
    """PlateMiterJoint between two coplanar (parallel) plates joining on one edge.

    Regression test: when the plates' faces are parallel and there is a gap, .
    """
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(11, 0, 0), Point(11, 10, 0), Point(20, 10, 0), Point(20, 0, 0), Point(11, 0, 0)])
    plate_b = Plate.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 2, "b_segment_index": 0}
    joint = PlateMiterJoint(plate_a, plate_b, **kwargs)
    joint.add_extensions()
    for plate in joint.elements:
        plate.apply_edge_extensions()

    assert isinstance(joint, PlateMiterJoint), "Expected joint to be a PlateMiterJoint"
    # plate_a's edge is the reference, so it should be unchanged...
    for point in plate_a.outline_a.points[2:4]:
        assert point.x == 10.5
    # ...while plate_b's edge should be pulled in to close the gap and meet it exactly
    for point in plate_b.outline_a.points[0:2]:
        assert point.x == 10.5


def test_three_plate_joints():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    plate_c = Plate.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    pairs = [(plate_a, plate_b), (plate_c, plate_b), (plate_a, plate_c)]
    topo_results = [cs.find_topology(px, py) for px, py in pairs]

    joints = []
    for (px, py), tr in zip(pairs, topo_results):
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(*_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateLButtJoint(*_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))

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
    pairs = [(plate_a, plate_b), (plate_c, plate_b), (plate_a, plate_c)]
    topo_results = [cs.find_topology(px, py) for px, py in pairs]

    joints = []
    for (px, py), tr in zip(pairs, topo_results):
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PlateMiterJoint(*_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PlateLButtJoint(*_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))

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
    pairs = [(plate_a, plate_b), (plate_c, plate_b), (plate_a, plate_c)]
    topo_results = [cs.find_topology(px, py) for px, py in pairs]

    model = TimberModel()
    model.add_elements([plate_a, plate_b, plate_c])
    model_joints = []
    for (px, py), tr in zip(pairs, topo_results):
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            model_joints.append(PlateMiterJoint.create(model, *_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            model_joints.append(PlateTButtJoint.create(model, *_ordered_plates(px, py, tr), topology=tr.topology, topology_data=tr))
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


def test_clear_extensions_skips_element_b_when_b_segment_index_is_none(mocker):
    """PlateTButtJoint never sets an extension plane on its cross plate (b_segment_index stays None),
    so clearing it must not touch the cross plate's extensions at all -- calling
    remove_blank_extension(None) would reset *every* edge of that plate, wiping out extensions
    that belong to other, unrelated joints on the same plate.
    """
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    joint = PlateTButtJoint(plate_a, plate_b, topology=JointTopology.TOPO_EDGE_FACE, a_segment_index=1, b_segment_index=None)
    spy_a = mocker.spy(plate_a, "remove_blank_extension")
    spy_b = mocker.spy(plate_b, "remove_blank_extension")

    joint.clear_extensions()

    spy_a.assert_called_once_with(1)
    spy_b.assert_not_called()
