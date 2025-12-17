from compas_timber.elements import Panel
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PanelMiterJoint
from compas_timber.connections import PanelTButtJoint
from compas.geometry import Polyline, Point


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_b = Panel.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PanelMiterJoint(panel_a, panel_b, **kwargs)
    joint.add_extensions()
    joint.add_features()
    for s in [panel_a, panel_b]:
        s.apply_edge_extensions()
    assert isinstance(joint, PanelMiterJoint), "Expected joint to be a PanelMiterJoint"
    assert any([panel_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to change outline_a"
    assert len(joint.interfaces) == 2, "Expected two interfaces to be created"
    assert len(panel_a.interfaces) == 1, "Expected panel_a to have the first interface"
    assert len(panel_b.interfaces) == 1, "Expected panel_b to have the second interface"
    panel_a.reset()
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to reset outline_a"
    assert len(panel_a.interfaces) == 0, "Expected panel_a to have no interfaces after reset"


def test_simple_joint_and_reset_no_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_b = Panel.from_outline_thickness(Polyline(polyline_b.points), 1)

    joint = PanelMiterJoint(panel_a, panel_b)
    joint.add_extensions()
    joint.add_features()
    for s in [panel_a, panel_b]:
        s.apply_edge_extensions()
    assert isinstance(joint, PanelMiterJoint), "Expected joint to be a PanelMiterJoint"
    assert len(joint.interfaces) == 2, "Expected two interfaces to be created"
    assert len(panel_a.interfaces) == 1, "Expected panel_a to have the first interface"
    assert len(panel_b.interfaces) == 1, "Expected panel_b to have the second interface"
    assert any([panel_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to change outline_a"
    panel_a.reset()
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_three_plate_joints():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    panel_c = Panel.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(panel_a, panel_b))
    topo_results.append(cs.find_topology(panel_c, panel_b))
    topo_results.append(cs.find_topology(panel_a, panel_c))

    joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PanelMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PanelTButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
    for j in joints:
        j.add_extensions()
        j.add_features()
    assert len(joints) == 3, "Expected three joints"
    assert all(isinstance(j, PanelMiterJoint) for j in joints), "Expected L-joints to be PanelMiterJoint"
    assert all([len(s.interfaces) == 2 for s in [panel_a, panel_b, panel_c]]), "Expected each panel to have two interfaces"


def test_three_plate_joints_mix_topo():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])

    panel_c = Panel.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(panel_a, panel_b))
    topo_results.append(cs.find_topology(panel_c, panel_b))
    topo_results.append(cs.find_topology(panel_a, panel_c))

    joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            joints.append(PanelMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            joints.append(PanelTButtJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))
    for j in joints:
        j.add_extensions()
        j.add_features()
    assert len(joints) == 3, "Expected three joints"
    assert isinstance(joints[0], PanelTButtJoint), "Expected L-joints to be PanelButtJoint"
    assert isinstance(joints[1], PanelMiterJoint), "Expected L-joints to be PanelMiterJoint"
    assert isinstance(joints[2], PanelMiterJoint), "Expected L-joints to be PanelMiterJoint"
    assert all([len(s.interfaces) == 2 for s in [panel_a, panel_b, panel_c]]), "Expected each panel to have two interfaces"


def test_panel_remove_interfaces():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    polyline_c = Polyline([Point(10, 0, 0), Point(20, 0, 10), Point(20, 20, 10), Point(10, 10, 0), Point(10, 0, 0)])
    panel_c = Panel.from_outline_thickness(polyline_c, 1)

    cs = PlateConnectionSolver()
    topo_results = []
    topo_results.append(cs.find_topology(panel_a, panel_b))
    topo_results.append(cs.find_topology(panel_c, panel_b))
    topo_results.append(cs.find_topology(panel_a, panel_c))

    joints = []
    for _a, _b in [[panel_a, panel_b], [panel_c, panel_b], [panel_a, panel_c]]:
        tr = cs.find_topology(_a, _b)
        joints.append(PanelMiterJoint(tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index))

    for j in joints:
        j.add_extensions()
        j.add_features()

    assert len(joints) == 3, "Expected three joints"
    assert all([len(s.interfaces) == 2 for s in [panel_a, panel_b, panel_c]]), "Expected each panel to have two interfaces"

    panel_a.remove_interfaces(joints[0].interfaces)
    assert len(panel_a.interfaces) == 1, "Expected panel_a to have one interface after removing one"
    assert len(panel_b.interfaces) == 2, "Expected panel_b to still have two interfaces"
    panel_b.remove_interfaces()
    assert len(panel_b.interfaces) == 0, "Expected panel_b to have no interfaces after removing all"
    assert len(panel_c.interfaces) == 2, "Expected panel_c to still have two interfaces"
    panel_c.remove_interfaces(joints[1].interfaces + joints[2].interfaces)
    assert len(panel_c.interfaces) == 0, "Expected panel_c to have no interfaces after removing both"
    assert len(panel_a.interfaces) == 1, "Expected panel_a to still have one interface"
