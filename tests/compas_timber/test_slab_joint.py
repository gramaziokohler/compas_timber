from compas_timber.elements import Slab
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import SlabMiterJoint
from compas_timber.connections import SlabTButtJoint
from compas.geometry import Polyline, Point


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    slab_a = Slab.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    slab_b = Slab.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = SlabMiterJoint(slab_a, slab_b, **kwargs)
    joint.add_extensions()
    joint.add_features()
    assert isinstance(joint, SlabMiterJoint), "Expected joint to be a SlabMiterJoint"
    assert any([slab_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to change outline_a"
    slab_a.reset()
    assert all([slab_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(slab_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_simple_joint_and_reset_no_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    slab_a = Slab.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    slab_b = Slab.from_outline_thickness(Polyline(polyline_b.points), 1)

    joint = SlabMiterJoint(slab_a, slab_b)
    joint.add_extensions()
    joint.add_features()
    assert isinstance(joint, SlabMiterJoint), "Expected joint to be a SlabMiterJoint"
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

    assert len(joints) == 3, "Expected three joints"
    assert all(isinstance(j, SlabMiterJoint) for j in joints), "Expected L-joints to be SlabMiterJoint"


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

    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], SlabTButtJoint), "Expected L-joints to be SlabButtJoint"
    assert isinstance(joints[1], SlabMiterJoint), "Expected L-joints to be SlabMiterJoint"
    assert isinstance(joints[2], SlabMiterJoint), "Expected L-joints to be SlabMiterJoint"
