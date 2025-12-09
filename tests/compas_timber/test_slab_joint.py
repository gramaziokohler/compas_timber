from compas_timber.elements import Slab
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import SlabMiterJoint
from compas_timber.connections import SlabTButtJoint
from compas_timber.connections import PlateJointCandidate
from compas_timber.model import TimberModel
from compas.geometry import Polyline, Point


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    slab_a = Slab.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    slab_b = Slab.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = SlabMiterJoint(slab_a, slab_b, **kwargs)
    joint.add_extensions()
    for s in [slab_a, slab_b]:
        s.apply_edge_extensions()
    joint.add_features()

    assert isinstance(joint, SlabMiterJoint), "Expected joint to be a SlabMiterJoint"
    assert any([slab_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to change outline_a"
    assert len(joint.interfaces) == 2, "Expected two interfaces to be created"
    assert len(slab_a.interfaces) == 1, "Expected slab_a to have the first interface"
    assert len(slab_b.interfaces) == 1, "Expected slab_b to have the second interface"
    slab_a.reset()
    assert all([slab_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to reset outline_a"
    assert len(slab_a.interfaces) == 0, "Expected slab_a to have no interfaces after reset"


def test_simple_joint_and_reset_no_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_b = Slab.from_outline_thickness(Polyline(polyline_b.points), 1)

    joint = SlabMiterJoint(slab_a, slab_b)
    joint.add_extensions()
    for s in [slab_a, slab_b]:
        s.apply_edge_extensions()
    joint.add_features()
    assert isinstance(joint, SlabMiterJoint), "Expected joint to be a SlabMiterJoint"
    assert len(joint.interfaces) == 2, "Expected two interfaces to be created"
    assert len(slab_a.interfaces) == 1, "Expected slab_a to have the first interface"
    assert len(slab_b.interfaces) == 1, "Expected slab_b to have the second interface"
    assert any([slab_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to change outline_a"
    slab_a.reset()
    assert all([slab_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_three_plate_joints():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_b = Slab.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    slab_c = Slab.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(slab_a, slab_b))
    topo_results.append(cs.find_topology(slab_c, slab_b))
    topo_results.append(cs.find_topology(slab_a, slab_c))

    joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(SlabMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(SlabTButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
    for j in joints:
        j.add_extensions()
        j.add_features()
    assert len(joints) == 3, "Expected three joints"
    assert all(isinstance(j, SlabMiterJoint) for j in joints), "Expected L-joints to be SlabMiterJoint"
    assert all([len(s.interfaces) == 2 for s in [slab_a, slab_b, slab_c]]), "Expected each slab to have two interfaces"


def test_three_plate_joints_mix_topo():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    slab_a = Slab.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    slab_b = Slab.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    slab_c = Slab.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(slab_a, slab_b))
    topo_results.append(cs.find_topology(slab_c, slab_b))
    topo_results.append(cs.find_topology(slab_a, slab_c))

    joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(SlabMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(SlabTButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
    for j in joints:
        j.add_extensions()
        j.add_features()
    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], SlabTButtJoint), "Expected L-joints to be SlabButtJoint"
    assert isinstance(joints[1], SlabMiterJoint), "Expected L-joints to be SlabMiterJoint"
    assert isinstance(joints[2], SlabMiterJoint), "Expected L-joints to be SlabMiterJoint"
    assert all([len(s.interfaces) == 2 for s in [slab_a, slab_b, slab_c]]), "Expected each slab to have two interfaces"


def test_slab_remove_interfaces():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_b = Slab.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    slab_c = Slab.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(slab_a, slab_b))
    topo_results.append(cs.find_topology(slab_c, slab_b))
    topo_results.append(cs.find_topology(slab_a, slab_c))

    joints = []
    for _a, _b in [[slab_a, slab_b], [slab_c, slab_b], [slab_a, slab_c]]:
        tr = cs.find_topology(_a, _b)
        joints.append(SlabMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))

    for j in joints:
        j.add_extensions()
    for s in [slab_a, slab_b, slab_c]:
        s.apply_edge_extensions()
    for j in joints:
        j.add_features()

    assert len(joints) == 3, "Expected three joints"
    assert all([len(s.interfaces) == 2 for s in [slab_a, slab_b, slab_c]]), "Expected each slab to have two interfaces"

    assert abs(slab_a.interfaces[0].width - 1.08239) < 0.01  # angle between plates = 45, miter angle is 22.5, 1/cos(22.5deg) = 1.08239...
    slab_a.remove_features(joints[0].interfaces)
    assert len(slab_a.interfaces) == 1, "Expected slab_a to have one interface after removing one"
    assert len(slab_b.interfaces) == 2, "Expected slab_b to still have two interfaces"
    slab_b.remove_features()
    assert len(slab_b.interfaces) == 0, "Expected slab_b to have no interfaces after removing all"
    assert len(slab_c.interfaces) == 2, "Expected slab_c to still have two interfaces"
    slab_c.remove_features(joints[1].interfaces + joints[2].interfaces)
    assert len(slab_c.interfaces) == 0, "Expected slab_c to have no interfaces after removing both"
    assert len(slab_a.interfaces) == 1, "Expected slab_a to still have one interface"


def test_slab_joint_candidate():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_b = Slab.from_outline_thickness(polyline_b, 1)

    model = TimberModel()
    model.add_elements([slab_a, slab_b])

    model.connect_adjacent_slabs()

    assert all((isinstance(j, PlateJointCandidate) for j in model.joints))  # TODO: do we want a `SlabJointCandidate`?

    assert len(model.joint_candidates) == 1
    edge_face_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_EDGE_FACE]
    assert len(edge_face_joints) == 1
    assert isinstance(edge_face_joints[0], PlateJointCandidate)
    assert edge_face_joints[0].topology == JointTopology.TOPO_EDGE_FACE
    assert list(model.joint_candidates)[0].elements[0] == slab_b
