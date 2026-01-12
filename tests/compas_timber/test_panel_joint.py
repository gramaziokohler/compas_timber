from compas.data import json_dumps, json_loads

from compas_timber.elements import Panel
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import PanelMiterJoint
from compas_timber.connections import PanelTButtJoint
from compas_timber.connections import PlateJointCandidate
from compas_timber.model import TimberModel
from compas.geometry import Polyline, Point


def test_simple_joint_and_reset():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(Polyline([pt for pt in polyline_a.points]), 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_b = Panel.from_outline_thickness(Polyline(polyline_b.points), 1)

    kwargs = {"topology": JointTopology.TOPO_EDGE_EDGE, "a_segment_index": 1, "b_segment_index": 0}
    joint = PanelMiterJoint(panel_a, panel_b, **kwargs)
    joint.add_extensions()
    for s in [panel_a, panel_b]:
        s.apply_edge_extensions()
    joint.add_features()

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
    for s in [panel_a, panel_b]:
        s.apply_edge_extensions()
    joint.add_features()
    assert isinstance(joint, PanelMiterJoint), "Expected joint to be a PanelMiterJoint"
    assert len(joint.interfaces) == 2, "Expected two interfaces to be created"
    assert len(panel_a.interfaces) == 1, "Expected panel_a to have the first interface"
    assert len(panel_b.interfaces) == 1, "Expected panel_b to have the second interface"
    assert any([panel_a.outline_a.points[i] != polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to change outline_a"
    panel_a.reset()
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected joint to reset outline_a"


def test_three_panel_joints():
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


def test_three_panel_joints_mix_topo():
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
    for p in [panel_a, panel_b, panel_c]:
        p.apply_edge_extensions()
    for j in joints:
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
    for s in [panel_a, panel_b, panel_c]:
        s.apply_edge_extensions()
    for j in joints:
        j.add_features()

    assert len(joints) == 3, "Expected three joints"
    assert all([len(s.interfaces) == 2 for s in [panel_a, panel_b, panel_c]]), "Expected each panel to have two interfaces"

    assert abs(panel_a.interfaces[0].width - 1.08239) < 0.01  # angle between plates = 45, miter angle is 22.5, 1/cos(22.5deg) = 1.08239...
    panel_a.remove_features(joints[0].interfaces)
    assert len(panel_a.interfaces) == 1, "Expected panel_a to have one interface after removing one"
    assert len(panel_b.interfaces) == 2, "Expected panel_b to still have two interfaces"
    panel_b.remove_features()
    assert len(panel_b.interfaces) == 0, "Expected panel_b to have no interfaces after removing all"
    assert len(panel_c.interfaces) == 2, "Expected panel_c to still have two interfaces"
    panel_c.remove_features(joints[1].interfaces + joints[2].interfaces)
    assert len(panel_c.interfaces) == 0, "Expected panel_c to have no interfaces after removing both"
    assert len(panel_a.interfaces) == 1, "Expected panel_a to still have one interface"


def test_panel_joint_candidate():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_b = Panel.from_outline_thickness(polyline_b, 1)

    model = TimberModel()
    model.add_elements([panel_a, panel_b])

    model.connect_adjacent_panels()

    assert all((isinstance(j, PlateJointCandidate) for j in model.joints))  # TODO: do we want a `PanelJointCandidate`?

    assert len(model.joint_candidates) == 1
    edge_face_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_EDGE_FACE]
    assert len(edge_face_joints) == 1
    assert isinstance(edge_face_joints[0], PlateJointCandidate)
    assert edge_face_joints[0].topology == JointTopology.TOPO_EDGE_FACE
    assert list(model.joint_candidates)[0].elements[0] == panel_b


def test_copy_three_panel_joints_mix_topo():
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

    model = TimberModel()
    model.add_elements([panel_a, panel_b, panel_c])
    model_joints = []
    for tr in topo_results:
        if tr.topology == JointTopology.TOPO_UNKNOWN:
            continue
        elif tr.topology == JointTopology.TOPO_EDGE_EDGE:
            model_joints.append(
                PanelMiterJoint.create(model, tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index)
            )
        elif tr.topology == JointTopology.TOPO_EDGE_FACE:
            model_joints.append(
                PanelTButtJoint.create(model, tr.plate_a, tr.plate_b, topology=tr.topology, a_segment_index=tr.a_segment_index, b_segment_index=tr.b_segment_index)
            )
    for j in model.joints:
        j.add_extensions()
    for p in [panel_a, panel_b, panel_c]:
        p.apply_edge_extensions()
    for j in model.joints:
        j.add_features()

    plines = []
    for p in model.panels:
        for i in p.interfaces:
            plines.append(i.geometry)

    assert len(model_joints) == 3, "Expected three joints"
    assert isinstance(model_joints[0], PanelTButtJoint), "Expected L-joints to be PanelButtJoint"
    assert isinstance(model_joints[1], PanelMiterJoint), "Expected L-joints to be PanelMiterJoint"
    assert isinstance(model_joints[2], PanelMiterJoint), "Expected L-joints to be PanelMiterJoint"
    assert all([len(s.interfaces) == 2 for s in [panel_a, panel_b, panel_c]]), "Expected each panel to have two interfaces"

    copy_model = json_loads(json_dumps(model))
    copy_joints = list(copy_model.joints)

    for p in copy_model.panels:
        assert len(p.interfaces) == 0, "Expected each panel to have two interfaces"

    for j in copy_joints:
        j.add_extensions()
    for p in copy_model.panels:
        p.apply_edge_extensions()
    for j in copy_joints:
        j.add_features()

    copy_plines = []
    for p in copy_model.panels:
        for i in p.interfaces:
            plines.append(i.geometry)

    for p, cp in zip(plines, copy_plines):
        for i in range(len(p)):
            assert p == cp, "Expected copied model to have same interface geometries"

    assert len(copy_joints) == 3, "Expected three joints"
    assert set([j.__class__ for j in copy_joints]) == set([PanelTButtJoint, PanelMiterJoint]), "Expected copied joints to have same types"
    for p in copy_model.panels:
        assert len(p.interfaces) == 2, "Expected each panel to have two interfaces"
