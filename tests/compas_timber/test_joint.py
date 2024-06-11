import os

import compas
import pytest
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import LButtJoint
from compas_timber.connections import LHalfLapJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import THalfLapJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.connections import find_neighboring_beams
from compas_timber.elements import Beam
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
        model.add_beam(b)
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
    model.add_beam(b1)
    model.add_beam(b2)
    _ = TButtJoint.create(model, b1, b2)

    assert len(model.beams) == 2
    assert len(model.joints) == 1


def test_deepcopy(mocker, t_topo_beams):
    mocker.patch("compas_timber.connections.Joint.add_features")
    assembly = TimberModel()
    beam_a, beam_b = t_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    t_butt = TButtJoint.create(assembly, beam_a, beam_b)
    assembly_copy = assembly.copy()

    assert assembly_copy is not assembly
    assert assembly_copy.beams
    assert assembly_copy.joints

    t_butt_copy = assembly_copy.joints[0]
    assert t_butt_copy is not t_butt
    assert t_butt_copy.beams


def test_joint_create_t_butt(t_topo_beams):
    assembly = TimberModel()
    main_beam, cross_beam = t_topo_beams
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)
    joint = TButtJoint.create(assembly, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.beams


def test_joint_create_l_butt(l_topo_beams):
    assembly = TimberModel()
    beam_a, beam_b = l_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = LButtJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_x_half_lap(x_topo_beams):
    assembly = TimberModel()
    beam_a, beam_b = x_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = XHalfLapJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_t_lap(t_topo_beams):
    assembly = TimberModel()
    main_beam, cross_beam = t_topo_beams
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)
    joint = THalfLapJoint.create(assembly, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.beams


def test_joint_create_l_lap(l_topo_beams):
    assembly = TimberModel()
    beam_a, beam_b = l_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = LHalfLapJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_kwargs_passthrough_lbutt():
    assembly = TimberModel()
    small = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), 0.1, 0.1, z_vector=Vector(0, 0, 1))
    large = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    assembly.add_beam(small)
    assembly.add_beam(large)

    # main beam butts by default, first beam is by default main, they are swapped if necessary when small_beam_butts=True
    joint_a = LButtJoint.create(assembly, small, large, small_beam_butts=True)

    assert joint_a.main_beam is small
    assert joint_a.cross_beam is large

    assembly.remove_joint(joint_a)

    joint_b = LButtJoint.create(assembly, small, large, small_beam_butts=False)

    assert joint_b.main_beam is small
    assert joint_b.cross_beam is large

    assembly.remove_joint(joint_b)

    joint_c = LButtJoint.create(assembly, large, small, small_beam_butts=True)

    assert joint_c.main_beam is small
    assert joint_c.cross_beam is large

    assembly.remove_joint(joint_c)

    joint_d = LButtJoint.create(assembly, large, small, small_beam_butts=False)

    assert joint_d.main_beam is large
    assert joint_d.cross_beam is small


def test_joint_create_kwargs_passthrough_xhalflap():
    assembly = TimberModel()
    beam_a = Beam.from_endpoints(Point(0.5, 0, 0), Point(0.5, 1, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    beam_b = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)

    joint = XHalfLapJoint.create(assembly, beam_a, beam_b, cut_plane_bias=0.4)

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
        result = find_neighboring_beams(example_model.beams)
        # beam objects => sets of keys for easy comparison
        key_sets = []
        for pair in result:
            a, b = pair
            key_sets.append({a.graph_node, b.graph_node})

        assert len(expected_result) == len(result)
        for pair in key_sets:
            assert pair in expected_result
