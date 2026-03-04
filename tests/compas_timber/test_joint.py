import os

import compas
import pytest
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.tolerance import TOL

from compas_timber.connections import JointCandidate
from compas_timber.connections import PlateJointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import TLapJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import find_neighboring_elements
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


@pytest.fixture
def example_model():
    path = os.path.abspath(r"data/lines.json")
    centerlines = json_load(path)
    w = 0.12
    h = 0.06
    model = TimberModel()
    for line in centerlines:
        b = Beam.from_centerline(line, w, h)
        model.add_element(b)
    return model


@pytest.fixture
def l_topo_beams():
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(x=0.0, y=1.0, z=0.0), Point(x=1.0, y=1.0, z=0.0)),
        Line(Point(x=1.0, y=1.0, z=0.0), Point(x=1.0, y=0.0, z=0.0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def t_topo_beams():
    w = 0.2
    h = 0.2
    cross = Line(Point(x=1.0, y=2.0, z=0.0), Point(x=3.0, y=2.0, z=0.0))
    main = Line(Point(x=2.0, y=2.0, z=0.0), Point(x=2.0, y=1.0, z=0.0))
    return Beam.from_centerline(main, w, h), Beam.from_centerline(cross, w, h)


@pytest.fixture
def x_topo_beams():
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(x=3.0, y=1.0, z=0.0), Point(x=4.0, y=0.0, z=0.0)),
        Line(Point(x=3.0, y=0.0, z=0.0), Point(x=4.0, y=1.0, z=0.0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


def test_create(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    # try create with beams
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    model.add_element(b1)
    model.add_element(b2)
    _ = TButtJoint.create(model, b1, b2)

    assert len(list(model.elements())) == 2
    assert len(list(model.joints)) == 1


def test_deepcopy(mocker, t_topo_beams):
    mocker.patch("compas_timber.connections.Joint.add_features")
    model = TimberModel()
    beam_a, beam_b = t_topo_beams
    model.add_element(beam_a)
    model.add_element(beam_b)
    t_butt = TButtJoint.create(model, beam_a, beam_b)
    model_copy = model.copy()

    assert model_copy is not model
    assert model_copy.beams
    assert model_copy.joints

    t_butt_copy = list(model_copy.joints)[0]
    assert t_butt_copy is not t_butt
    assert t_butt_copy.elements


def test_joint_create_t_butt(t_topo_beams):
    model = TimberModel()
    main_beam, cross_beam = t_topo_beams
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = TButtJoint.create(model, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.elements


def test_joint_create_l_butt(l_topo_beams):
    model = TimberModel()
    beam_a, beam_b = l_topo_beams
    model.add_element(beam_a)
    model.add_element(beam_b)
    joint = LButtJoint.create(model, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.elements


def test_joint_create_x_lap(x_topo_beams):
    model = TimberModel()
    main_beam, cross_beam = x_topo_beams
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = XLapJoint.create(model, main_beam, cross_beam)

    assert joint.beam_a is main_beam
    assert joint.beam_b is cross_beam
    assert joint.elements


def test_joint_create_t_lap(t_topo_beams):
    model = TimberModel()
    main_beam, cross_beam = t_topo_beams
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = TLapJoint.create(model, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.elements


def test_joint_create_l_lap(l_topo_beams):
    model = TimberModel()
    main_beam, cross_beam = l_topo_beams
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = LLapJoint.create(model, main_beam, cross_beam)

    assert joint.beam_a is main_beam
    assert joint.beam_b is cross_beam
    assert joint.elements


def test_joint_create_kwargs_passthrough_lbutt():
    model = TimberModel()
    small = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), 0.1, 0.1, z_vector=Vector(0, 0, 1))
    large = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    model.add_element(small)
    model.add_element(large)

    # main beam butts by default, first beam is by default main, they are swapped if necessary when small_beam_butts=True
    joint_a = LButtJoint.create(model, small, large, small_beam_butts=True)

    assert joint_a.main_beam is small
    assert joint_a.cross_beam is large

    model.remove_joint(joint_a)

    joint_b = LButtJoint.create(model, small, large, small_beam_butts=False)

    assert joint_b.main_beam is small
    assert joint_b.cross_beam is large

    model.remove_joint(joint_b)

    joint_c = LButtJoint.create(model, large, small, small_beam_butts=True)

    assert joint_c.main_beam is small
    assert joint_c.cross_beam is large

    model.remove_joint(joint_c)

    joint_d = LButtJoint.create(model, large, small, small_beam_butts=False)

    assert joint_d.main_beam is large
    assert joint_d.cross_beam is small


def test_joint_create_kwargs_passthrough_xhalflap():
    model = TimberModel()
    beam_a = Beam.from_endpoints(Point(0.5, 0, 0), Point(0.5, 1, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    beam_b = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    model.add_element(beam_a)
    model.add_element(beam_b)

    joint = XLapJoint.create(model, beam_a, beam_b, cut_plane_bias=0.4)

    assert joint.cut_plane_bias == 0.4


if not compas.IPY:

    def test_find_neighbors(example_model):
        expected_result = [
            set([0, 1]),
            set([0, 3]),
            set([1, 2]),
            set([1, 4]),
            set([1, 5]),
            set([2, 3]),
            set([2, 6]),
            set([3, 4]),
            set([3, 5]),
            set([5, 6]),
        ]
        result = find_neighboring_elements(list(example_model.beams))
        # beam objects => sets of keys for easy comparison
        key_sets = []
        for pair in result:
            a, b = pair
            key_sets.append({a.graphnode, b.graphnode})

        assert len(expected_result) == len(result)
        for pair in key_sets:
            assert pair in expected_result


def test_generic_joint():
    w, h = 20, 20

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
    ]

    model = TimberModel()
    model.add_elements([Beam.from_centerline(line, w, h) for line in lines])

    model.connect_adjacent_beams()

    # Joint candidates should be stored separately from actual joints
    assert all((isinstance(j, JointCandidate) for j in model.joint_candidates))
    assert len(model.joint_candidates) == 4
    assert len(model.joints) == 0  # No actual joints should be created

    l_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_L]
    x_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_X]
    assert len(l_joints) == 3
    assert len(x_joints) == 1

    for j in l_joints:
        assert TOL.is_allclose(j.location, Point(x=-10.0, y=-10.0, z=0.0))
    for j in x_joints:
        assert TOL.is_allclose(j.location, Point(x=107.24142664116566, y=69.42161159562835, z=0.0))


def test_plate_joint_candidate():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    model = TimberModel()
    model.add_elements([plate_a, plate_b])

    model.connect_adjacent_plates()

    assert all((isinstance(j, PlateJointCandidate) for j in model.joints))

    assert len(model.joint_candidates) == 1
    edge_face_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_EDGE_FACE]
    assert len(edge_face_joints) == 1
    assert isinstance(edge_face_joints[0], PlateJointCandidate)
    assert edge_face_joints[0].topology == JointTopology.TOPO_EDGE_FACE
    assert list(model.joint_candidates)[0].elements[0] == plate_b


def test_joint_candidate_create_still_works():
    """Test that JointCandidate.create() still works for creating actual joints."""
    w, h = 20, 20

    lines = [
        Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1.0, y=0.0, z=0.0)),
        Line(Point(x=0.5, y=-0.5, z=0.0), Point(x=0.5, y=0.5, z=0.0)),
    ]

    model = TimberModel()
    beams = [Beam.from_centerline(line, w, h) for line in lines]
    model.add_elements(beams)

    # JointCandidate.create() should still create actual joints
    joint = JointCandidate.create(model, beams[0], beams[1], topology=JointTopology.TOPO_T, location=Point(0.5, 0, 0))

    assert isinstance(joint, JointCandidate)
    assert joint in model.joints  # Should be in actual joints
    assert len(model.joints) == 1
    assert len(model.joint_candidates) == 0  # Should not be in candidates
